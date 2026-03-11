lav et streamlit dashboard. Overskriften skal "RSV og influenza i Danmark". Tilføj favicon der passer til sygdom/virus. Layout skal være friskt, men stadig professionelt. 

Det skal hente data fra <https://steenhulthin.github.io/infectious-diseases-data/> . Data skal hentes med pandas som beskrevet i readme.md her: <https://github.com/steenhulthin/infectious-diseases-data>. Brug influenza epikurven:  <https://steenhulthin.github.io/infectious-diseases-data/02_influenza_epikurve_season_region_uge_agegrp.csv> og rsv epikurven: <https://steenhulthin.github.io/infectious-diseases-data/02_rsv_epikurve_season_region_uge_agegrp.csv>. 

Brug kun influenza A tal. 

På dashboardet skal der være følgende filtre: 
- periode (dobbelt slider)
- aldersgruppe (single select)
- region (single select)

Der skal være grafer på dashboardet. Grafer skal være plotly grafer.

Graf 1 skal vise incidens for RSV og influenza over tid. Det skal være interaktivt med filtrene.

Graf 2 skal være et scatterplot med incedens af RSV mod incidens for influenza. 

