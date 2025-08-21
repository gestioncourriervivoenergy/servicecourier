def clean_email(email_str: str) -> str | None:
    if not email_str:
        return None

    raw = str(email_str).strip().lower()

    vivo_json = {
        "kader_maiga": "Kader.Maiga@VivoEnergy.com",
        "jessica_brou": "jessica.brou@vivoenergy.com",
        "regine_nogbou": "Regine.Nogbou@vivoenergy.com",
        "konan_ngoran": "Konan.Ngoran@vivoenergy.com",
        "armand_seri": "Armand.Seri@vivoenergy.com",
        "jean_bohoussou": "Jean.Bohoussou@vivoenergy.com",
        "juvenal_guei": "Juvenal.Guei@vivoenergy.com",
        "jean_paul_nobou": "Jean-Paul.Nobou@vivoenergy.com",
        "sidonie_gnammon": "Sidonie.Gnammon@vivoenergy.com",
        "bernadin_kouassi": "bernadin.kouassi@vivoenergy.com",
        "solange_gbeuly": "Solange.Gbeuly@vivoenergy.com",
        "emma_yapi": "Emma.Yapi@vivoenergy.com",
        "charles_tape": "Charles.Tape@vivoenergy.com",
        "christophe_dia": "Christophe.Dia@vivoenergy.com",
        "brehima_kone": "Brehima.Kone@vivoenergy.com",
        "frederic_kouadio": "Frederic.Kouadio@vivoenergy.com",
        "emmanuella_kouame": "emmanuella.kouame@vivoenergy.com",
        "paule_irene_diallo": "Paule-Irene.Diallo@vivoenergy.com",
        "eunice_achie": "eunice.achie@vivoenergy.com",
        "eunice_achie_vivoenergy_com": "eunice.achie@vivoenergy.com",
        "emma_yapi_vivoenergy_com":"Emma.Yapi@vivoenergy.com"

        
    }

    corrections = {
        "_gmail_com": "@gmail.com",
        "_yahoo_com": "@yahoo.com",
        "_outlook_com": "@outlook.com",
    }

    # Correct domains
    for key, value in corrections.items():
        raw = raw.replace(key, value)

    # Extract local part before @
    local_part = raw.split("@")[0]

    # Try matching against vivo_json
    if local_part in vivo_json:
        return vivo_json[local_part]

    return raw
