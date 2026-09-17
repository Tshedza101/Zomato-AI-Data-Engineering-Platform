select 
restuarant_id, 
restuarant_name, 
city, cuisine, 
rating, 
rating_count, 
cost_for_two
from {{ ref('stg_restuarants') }}