"""
Module contains sql queries that will pull from big query
"""

GAS_BURN_QUERY = """
select
    upper(position.marketarea) as marketarea, 
    ngquantity.begtime as gas_day, 
    sum(ngquantity.energy) as energy,
    
from
    bepc-prj-energy-prod.bepc_bq_energy_model.Trade as trade
inner join 
    bepc-prj-energy-prod.bepc_bq_energy_model.Position as position ON trade.trade = position.trade
inner join
    bepc-prj-energy-prod.`bepc_bq_energy_model.NG_Quantity` as ngquantity ON position.position = ngquantity.position
where 1=1
    AND position.bepc_strategy = "Burn" 
    AND trade.tradestatus <> "Void"
    AND ngquantity.posstatus = TRUE
    AND ngquantity.begtime BETWEEN @start_date and @end_date
    AND position.marketarea not in ("Bison", "Cottage Grove")
group by all
order by ngquantity.begtime
"""
  
NON_PGS_GENERATION_QUERY = """
select 
        begtime, 
        loadshape, 
        he1 as he01,
        he2 as he02,
        he3 as he03,
        he4 as he04,
        he5 as he05,
        he6 as he06,
        he7 as he07,
        he8 as he08,
        he9 as he09,
        he10 as he10,
        he11 as he11,
        he12 as he12,
        he13 as he13,
        he14 as he14,
        he15 as he15,
        he16 as he16,
        he17 as he17,
        he18 as he18,
        he19 as he19,
        he20 as he20,
        he21 as he21,
        he22 as he22,
        he23 as he23,
        he24 as he24
from bepc-prj-energy-prod.bepc_bq_energy_model.Loadshape_Profile
where 1=1
        and begtime between @start_date and @end_date
        and loadshape IN ('WAUE.BEPM.DCS1 - Net Generation',
                'WAUE.BEPM.LCS1 - Net Generation', 'WAUE.BEPM.LCS2 - Net Generation', 'WAUE.BEPM.LCS3 - Net Generation', 'WAUE.BEPM.LCS4 - Net Generation', 'WAUE.BEPM.LCS5 - Net Generation',
                'WAUE.BEPM.LCS6 - Net Generation', 'WAUE.BEPM.GGS1 - Net Generation', 'WAUE.BEPM.GGS2 - Net Generation', 'WAUE.BEPM.CULBERTSON1 - Net Generation')
group by all
"""


PGS_GENERATION_QUERY = """
SELECT 
  begtime, 
  loadshape, 
  SUM(he1) as he01,
  SUM(he2) as he02,
  SUM(he3) as he03,
  SUM(he4) as he04,
  SUM(he5) as he05,
  SUM(he6) as he06,
  SUM(he7) as he07,
  SUM(he8) as he08,
  SUM(he9) as he09, 
  SUM(he10) as he10, 
  SUM(he11) as he11, 
  SUM(he12) as he12, 
  SUM(he13) as he13, 
  SUM(he14) as he14, 
  SUM(he15) as he15, 
  SUM(he16) as he16,
  SUM(he17) as he17, 
  SUM(he18) as he18, 
  SUM(he19) as he19, 
  SUM(he20) as he20, 
  SUM(he21) as he21, 
  SUM(he22) as he22, 
  SUM(he23) as he23, 
  SUM(he24) as he24

FROM bepc-prj-energy-prod.bepc_bq_energy_model.Loadshape_Profile

WHERE loadshape LIKE '%PGS%' AND loadshape LIKE '%- Net Generation-5m' AND begtime between @start_date and @end_date

GROUP BY begtime, loadshape

ORDER BY loadshape, begtime
"""