select 
    f.restuarant_id, r.restuarant_name, r.city, r.cuisine, 
    count(*) as orders,
    sum(iff(f.is_delivered, f.sales_amount, 0)) as revenue, 
    round(avg(f.customer_rating),2) as avg_customer_rating,
    round(avg(f.delivery_time_min),1) as avg_delivery_min
from {{ ref('fact_orders') }} f 
left join {{ ref('dim_restuarants') }} r using (restuarant_id) 
group by 1,2,3,4