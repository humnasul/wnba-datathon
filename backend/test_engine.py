import tempfile
from pathlib import Path
import pandas as pd
from recommendation_model import GravityRecommender

with tempfile.TemporaryDirectory() as d:
    path=Path(d)
    pd.DataFrame([{'Team_ID':1,'Team_Abbreviation':'MIN','Team_Full_Name':'Minnesota Lynx'}]).to_csv(path/'wnba_team_lookup.csv',index=False)
    pd.DataFrame([{'playerId':p,'Full_Name':n} for p,n in [(10,'Star Player'),(11,'Candidate A'),(12,'Candidate B')]]).to_csv(path/'wnba_player_lookup.csv',index=False)
    rows=[]
    for game in range(1,11):
        for pid,offset in [(10,0),(11,.4),(12,7)]:
            if pid==10 and game>7: continue
            row={'Game_ID':game,'teamId':1,'playerId':pid,'frames':1500,'averageGravity':5+offset}
            for prefix in ['onBallPerimeter','offBallPerimeter','onBallInterior','offBallInterior']:
                row[prefix+'_Frames']=350
                row[prefix+'_averageGravity']=5+offset
            rows.append(row)
    pd.DataFrame(rows).to_csv(path/'wnba_gravity_by_game.csv',index=False)
    engine=GravityRecommender(path)
    result=engine.recommend('MIN','Star Player')
    assert result['recommendations'][0]['player_name']=='Candidate A'
    assert result['recommendations'][0]['with_without_star']['games_star_not_recorded']==3
    assert result['recommendations'][0]['with_without_star']['difference'] is not None
    print('PASS: closer role-fit candidate ranks first')
    print('PASS: with/without-game exploratory comparison computed')
    print('PASS: JSON-safe result with',len(result['recommendations']),'recommendations')
