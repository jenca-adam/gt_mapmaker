import gt_mapmaker
RES = 0.2
for _,country in gt_mapmaker.countries.iterrows():
    print(country)
    trigrid = gt_mapmaker.MultiTriGrid.build(country.geometry, RES)
    trigrid.dump(f"gt_mapmaker/data/grids/{country.iso_a2}.pickle")
