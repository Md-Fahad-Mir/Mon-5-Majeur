from django.contrib import admin
from .models import (
    MatchModel, MatchScoreModel, MatchPair, LeagueSeason, PlayoffQualification,
    PublicMatchModel, PublicMatchScoreModel, PublicMatchPair, PublicLeagueSeason, PublicPlayoffQualification
)

# Private League Models
admin.site.register(MatchModel)
admin.site.register(MatchScoreModel)
admin.site.register(MatchPair)
admin.site.register(LeagueSeason)
admin.site.register(PlayoffQualification)

# Public League Models
admin.site.register(PublicMatchModel)
admin.site.register(PublicMatchScoreModel)
admin.site.register(PublicMatchPair)
admin.site.register(PublicLeagueSeason)
admin.site.register(PublicPlayoffQualification)
