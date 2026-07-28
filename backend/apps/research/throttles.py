from rest_framework.throttling import UserRateThrottle


class ResearchHourlyThrottle(UserRateThrottle):
    scope = "research_hourly"


class ResearchDailyThrottle(UserRateThrottle):
    scope = "research_daily"
