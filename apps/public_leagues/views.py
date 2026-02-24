from django.db import models
from .models import PublicLeagueModel
from .serializers import PublicLeagueSerializer, JoinPublicLeagueSerializer, LeavePublicLeagueSerializer, PublicKickTeamSerializer, PublicStartLeagueSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from core.custom_permission import IsOwner
from drf_yasg.utils import swagger_auto_schema
from django.utils import timezone

# helper function for websocket consumers
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Match scheduler
from apps.matches.services import MatchSchedulerService


def broadcast_league_event(league_id, event, payload):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"public_league_{league_id}",
        {
            "type": "broadcast",
            "event": event,
            "payload": payload,
        }
    )


class PublicLeagueViewSet(ModelViewSet):
    serializer_class = PublicLeagueSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        # Short-circuit when schema is being generated
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return PublicLeagueModel.objects.none()
        
        user_profile = self.request.user.userprofile
        
        # If retrieving a specific league, allow if user is creator OR a member
        if self.action == 'retrieve':
            return PublicLeagueModel.objects.filter(models.Q(creator=user_profile) | models.Q(teams=user_profile)).prefetch_related('public_matches').distinct()
        
        # Default: Only leagues created by logged-in user (for list, etc.)
        return PublicLeagueModel.objects.filter(creator=user_profile).prefetch_related('public_matches')

    def get_permissions(self):
        """
        Custom permissions:
        - retrieve: IsAuthenticated (member check is handled in get_queryset)
        - update/partial_update/destroy: IsAuthenticated and IsOwner
        - other actions: As defined in permission_classes
        """
        if self.action == 'retrieve':
            return [IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwner()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user_profile = self.request.user.userprofile
        # Auto-attach creator
        league = serializer.save(creator=user_profile)
        league.teams.add(user_profile)  # Creator automatically joins their own league

    def perform_update(self, serializer):
        # Ensure only owner can update
        if serializer.instance.creator != self.request.user.userprofile:
            raise PermissionDenied("You cannot edit this league.")
        serializer.save()

    def perform_destroy(self, instance):
        # Ensure only owner can delete
        if instance.creator != self.request.user.userprofile:
            raise PermissionDenied("You cannot delete this league.")
        instance.delete()

    # List active leagues available to join
    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def active_leagues(self, request):
        active_leagues = (
        PublicLeagueModel.objects.filter(
            is_active=True,
            is_started=False,
        )
        .exclude(creator=request.user.userprofile)
        .exclude(teams=request.user.userprofile)
        .prefetch_related('public_matches')
        )
        
        serializer = PublicLeagueSerializer(active_leagues, many=True)
        return Response(serializer.data, status=200)

    # Join a public league (no code required)
    @swagger_auto_schema(request_body=JoinPublicLeagueSerializer)
    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def join(self, request):
        league_id = request.data.get('league_id')
        if not league_id:
            return Response({"detail": "League ID is required."}, status=400)

        try:
            league = PublicLeagueModel.objects.get(pk=league_id)
        except PublicLeagueModel.DoesNotExist:
            return Response({"detail": "League not found."}, status=404)
        
        team = request.user.userprofile

        if league.is_started or not league.is_active:
            return Response({"detail": "Cannot join this league."}, status=400)

        if team in league.teams.all():
            return Response({"detail": "You are already a member of this league."}, status=400)

        if league.teams.count() >= int(league.max_team_number):
            return Response({"detail": "This league is full."}, status=400)
        
        league.teams.add(team)
        league.save()

        # Broadcast to websocket consumers that a new team has joined
        broadcast_league_event(
            league_id=league.id,
            event="team_joined",
            payload={
                "user": getattr(team.user, 'username', None),
                "team_id": team.id,
                "team_name": team.team_name,
                "team_logo": getattr(team, 'team_logo', None),
            }
        )

        return Response({"detail": "Successfully joined the league."}, status=200)
    
    # List leagues the user has joined
    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def my_leagues(self, request):
        user_profile = request.user.userprofile
        leagues = PublicLeagueModel.objects.filter(teams=user_profile).prefetch_related('public_matches')
        serializer = PublicLeagueSerializer(leagues, many=True)
        return Response(serializer.data, status=200)

    # Leave a public league
    @swagger_auto_schema(request_body=LeavePublicLeagueSerializer)
    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def leave(self, request, pk=None):
        try:
            league = PublicLeagueModel.objects.get(pk=request.data.get('league_id'))
        except PublicLeagueModel.DoesNotExist:
            return Response({"detail": "League not found."}, status=404)
        
        team = request.user.userprofile

        if team == league.creator:
            return Response({"detail": "League creator cannot leave their own league."}, status=400)

        if team not in league.teams.all():
            return Response({"detail": "You are not a member of this league."}, status=400)

        league.teams.remove(team)
        league.save()

        # Broadcast to websocket consumers that a team has left
        broadcast_league_event(
            league_id=league.id,
            event="team_left",
            payload={
                "user": getattr(team.user, 'username', None),
                "team_id": team.id,
                "team_name": team.team_name,
                "team_logo": getattr(team, 'team_logo', None),
            }
        )

        return Response({"detail": "Successfully left the league."}, status=200)
    
    # kick a team from the league (creator only)
    @swagger_auto_schema(request_body=PublicKickTeamSerializer)
    @action(
        detail=False,
        methods=['post'],   
        permission_classes=[IsAuthenticated, IsOwner]
    )
    def kick(self, request, pk=None):
        try:
            league = PublicLeagueModel.objects.get(pk=request.data.get('league_id'))
        except PublicLeagueModel.DoesNotExist:
            return Response({"detail": "League not found."}, status=404)
        
        team_id = request.data.get('team_id')
        try:
            team = league.teams.get(id=team_id)
        except UserProfile.DoesNotExist:
            return Response({"detail": "Team not found in this league."}, status=404)

        if request.user.userprofile != league.creator:
            return Response({"detail": "Only the league creator can kick teams."}, status=403)

        league.teams.remove(team)
        league.save()

        # Broadcast to websocket consumers that a team has been kicked
        broadcast_league_event(
            league_id=league.id,
            event="team_kicked",
            payload={
                "user": getattr(team.user, 'username', None),
                "team_id": team.id,
                "team_name": team.team_name,
                "team_logo": getattr(team, 'team_logo', None),
            }
        )

        return Response({"detail": f"Successfully kicked {team.team_name} from the league."}, status=200)
    
    # Start the league (creator only)
    @swagger_auto_schema(request_body=PublicStartLeagueSerializer)
    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated, IsOwner]
    )
    def start_league(self, request, pk=None):
        try:
            league = PublicLeagueModel.objects.get(pk=request.data.get('league_id'))
        except PublicLeagueModel.DoesNotExist:
            return Response({"detail": "League not found."}, status=404)
        
        if request.user.userprofile != league.creator:
            return Response({"detail": "Only the league creator can start the league."}, status=403)

        if league.is_started:
            return Response({"detail": "League has already started."}, status=400)

        if league.teams.count() < 2:
            return Response({"detail": "At least two teams are required to start the league."}, status=400)

        try:
            # Initialize season with NBA metadata
            MatchSchedulerService.initialize_public_season(league)
        except Exception as e:
            return Response(
                {"detail": f"Failed to initialize season: {str(e)}"}, 
                status=500
            )
        # Generate matches for the entire season
        try:
            MatchSchedulerService.generate_public_season_matches(league)
        except Exception as e:
            # If match generation fails, we might want to rollback or at least log/notify
            # For now, let's allow it but maybe add a warning to the response if needed
            print(f"Match generation warning: {e}")

        league.is_started = True
        league.start_date = timezone.now()
        league.save()

        # Broadcast to websocket consumers that the league has started
        broadcast_league_event(
            league_id=league.id,
            event="league_started",
            payload={
                "message": "The league has started!",
            }
        )

        return Response({"detail": "League started successfully."}, status=200)
