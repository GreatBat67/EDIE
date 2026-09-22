-- Resume children first, then root
ALTER TASK INSURANCE_AI_HUB.ANALYTICS.DAILY_REFRESH_VEHICLE_DETAILS RESUME;
ALTER TASK INSURANCE_AI_HUB.ANALYTICS.DAILY_REFRESH_CUSTOMER_ATTR_HISTORY RESUME;
ALTER TASK INSURANCE_AI_HUB.ANALYTICS.DAILY_REFRESH_CLAIM_ACTIVITY_LOG RESUME;
ALTER TASK INSURANCE_AI_HUB.ANALYTICS.DAILY_UPDATE_FRICTION_REASON RESUME;
ALTER TASK INSURANCE_AI_HUB.ANALYTICS.DAILY_REFRESH_ML_MODELS RESUME;
ALTER TASK INSURANCE_AI_HUB.ANALYTICS.DAILY_ENRICHMENT_ROOT RESUME;



Most Impactful for Your Insurance AI Hub
If I were to pick the top 5 you should consider for Phase 2:

Analytical Search on your EDIE agent — upgrade from basic Cortex Search to corpus-wide analysis across all policy documents
Cortex Agent Code Execution — let EDIE agent write and run Python to create charts, do statistics, train models on-the-fly
Per-user Quotas — protect against runaway AI costs when you roll this out to multiple users
Semantic View Materializations — speed up agent queries by materializing your semantic views
CoCo Automations — schedule automated weekly reports that run the executive brief generator on a cron
Want me to implement any of these for Phase 2?