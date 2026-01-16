select
	team_short,
	team_name
from {{ source('landing', 'fantrax_team_names') }}
