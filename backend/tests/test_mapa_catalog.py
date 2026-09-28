from app.connectors.mapa_catalog import load_catalog


def test_load_catalog_reads_official_snapshot_csv(tmp_path):
    catalog = tmp_path / "mapa.csv"
    catalog.write_text(
        "id,commercial_name,active_substance,dose,safety_period_days,crop_type,disease_code\n"
        "123,Cobre autorizado,Cobre,2 kg/ha,14,olivar,repilo\n",
        encoding="utf-8",
    )

    products = load_catalog(catalog)

    assert len(products) == 1
    assert products[0].id == "123"
    assert products[0].commercial_name == "Cobre autorizado"
    assert products[0].safety_period_days == 14


def test_load_catalog_missing_file_returns_empty_list(tmp_path):
    assert load_catalog(tmp_path / "missing.csv") == []
