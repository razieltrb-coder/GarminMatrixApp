"""
Estrattore dati Garmin - FIX 429 + FULL DATA per Gemini + Load Focus VERO 2026
NO VALORI FISSI - tutto reale da API
"""

import json
import os
import time
from datetime import date, timedelta
from getpass import getpass
from pathlib import Path
from garminconnect import Garmin

GIORNI_PRIMA_VOLTA = 1400
GIORNI_AGGIORNAMENTO = 30
FILE_DATABASE = os.path.join(os.environ.get("ANDROID_PRIVATE","."), "database.json")
TOKEN_DIR = os.path.join(os.environ.get("ANDROID_PRIVATE","."), ".garmin_tokens")

def accedi():
    try:
        print(f"Provo login con token da {TOKEN_DIR}...")
        api = Garmin()
        api.login(TOKEN_DIR)
        print("✓ Accesso con token salvati - OK, niente 429")
        return api
    except Exception as e:
        print(f"Token non valido o scaduto: {e}")
    print("Login con email/password richiesto.")
    print("Attendo 5 sec per evitare blocco Garmin...")
    time.sleep(5)
    email = input("Email Garmin: ").strip()
    password = getpass("Password Garmin: ")
    api = Garmin(email=email, password=password, prompt_mfa=lambda: input("Codice MFA: ").strip(),)
    try:
        api.login(TOKEN_DIR)
        print("Accesso riuscito, token salvati.")
        return api
    except Exception as e:
        print(f"Errore login: {e}")
        print("Se vedi 429, ASPETTA 1 ORA prima di riprovare!")
        raise

def prova(funzione, *args):
    try:
        time.sleep(0.3)
        return funzione(*args)
    except Exception as e:
        if "429" in str(e) or "TooManyRequests" in str(e):
            print(" ⚠ 429 rilevato, attendo 30 sec...")
            time.sleep(30)
        return None

def riassumi_attivita(a):
    tipo = (a.get("activityType") or {}).get("typeKey")
    tipo_parent = (a.get("activityType") or {}).get("parentTypeKey")
    return {
        "activityId": a.get("activityId"),
        "nome": a.get("activityName"),
        "tipo": tipo,
        "tipo_parent": tipo_parent,
        "inizio": a.get("startTimeLocal"),
        "inizio_gmt": a.get("startTimeGMT"),
        "distanza_m": a.get("distance"),
        "durata_s": a.get("duration"),
        "durata_elapsed_s": a.get("elapsedDuration"),
        "durata_movimento_s": a.get("movingDuration"),
        "calorie": a.get("calories"),
        "calorie_attive": a.get("activeCalories"),
        "fc_media": a.get("averageHR"),
        "fc_max": a.get("maxHR"),
        "fc_min": a.get("minHR"),
        "velocita_media_m_s": a.get("averageSpeed"),
        "velocita_max_m_s": a.get("maxSpeed"),
        "cadenza_media": a.get("averageRunCadence") or a.get("averageBikingCadenceInRevPerMinute") or a.get("averageBikingCadence"),
        "cadenza_max": a.get("maxRunCadence") or a.get("maxBikingCadenceInRevPerMinute") or a.get("maxBikingCadence"),
        "cadenza_media_bici": a.get("averageBikingCadenceInRevPerMinute"),
        "passi": a.get("steps"),
        "passi_medio": a.get("averageStepsPerMinute"),
        "potenza_media_w": a.get("avgPower"),
        "potenza_max_w": a.get("maxPower"),
        "potenza_normalizzata_w": a.get("normPower"),
        "potenza_20min_w": a.get("power_20min"),
        "dislivello_positivo_m": a.get("elevationGain"),
        "dislivello_negativo_m": a.get("elevationLoss"),
        "quota_min_m": a.get("minElevation"),
        "quota_max_m": a.get("maxElevation"),
        "training_effect_aerobico": a.get("aerobicTrainingEffect"),
        "training_effect_anaerobico": a.get("anaerobicTrainingEffect"),
        "training_effect_label": a.get("trainingEffectLabel"),
        "training_load": a.get("activityTrainingLoad"),
        "training_load_acute": a.get("acwrFactor"),
        "vo2max_attivita": a.get("vO2MaxValue"),
        "respirazione_media": a.get("avgRespirationRate"),
        "respirazione_max": a.get("maxRespirationRate"),
        "temperatura_media": a.get("avgTemperature"),
        "temperatura_max": a.get("maxTemperature"),
        "gradi_salita_media": a.get("avgGradeAdjustedSpeed") or a.get("avgGrade"),
        "velocita_verticale_media": a.get("avgVerticalSpeed"),
        "raw": a,
    }

def riassumi_giorno(api, giorno):
    s = prova(api.get_user_summary, giorno) or {}
    sleep_full = prova(api.get_sleep_data, giorno) or {}
    sonno = sleep_full.get("dailySleepDTO") or {}
    punteggio = (sonno.get("sleepScores") or {}).get("overall") or {}
    hrv_data = prova(api.get_hrv_data, giorno) or {}
    hrv_val = None
    hrv_status = None
    try:
        summary = hrv_data.get("hrvSummary") or hrv_data
        hrv_val = summary.get("lastNightAvg") or summary.get("weeklyAvg") or summary.get("lastNight5MinHigh")
        hrv_status = summary.get("hrvStatus")
        if hrv_val is None and hrv_data.get("hrvReadings"):
            hrv_val = hrv_data["hrvReadings"][-1].get("hrvValue")
    except: pass
    resp_data = prova(api.get_respiration_data, giorno) or {}
    stress_data = prova(api.get_stress_data, giorno) or {}
    bb_data = prova(api.get_body_battery, giorno) or []
    spo2_data = prova(api.get_spo2_data, giorno) or {}
    vo2 = None
    training_status_label = None
    acute_load = None
    chronic_load = None
    try:
        ts = prova(api.get_training_status, giorno) or {}
        if ts.get("mostRecentVO2Max"):
            vo2 = ts["mostRecentVO2Max"].get("generic", {}).get("vo2MaxValue") or ts["mostRecentVO2Max"].get("running", {}).get("vo2MaxValue") or ts["mostRecentVO2Max"].get("cycling", {}).get("vo2MaxValue")
        training_status_label = ts.get("mostRecentTrainingStatus",{}).get("trainingStatusFeedbackPhrase") or ts.get("trainingStatusFeedbackPhrase")
        if ts.get("mostRecentTrainingLoadBalance"):
            acute_load = ts.get("mostRecentAcuteLoad")
            chronic_load = ts.get("mostRecentChronicLoad")
    except: pass
    readiness = None
    try:
        tr = prova(api.get_training_readiness, giorno) or {}
        readiness = tr.get("score") if isinstance(tr, dict) else (tr[0].get("score") if isinstance(tr, list) and tr else None)
    except: pass
    peso = None
    try:
        w = prova(api.get_daily_weigh_ins, giorno) or {}
        if w.get("dateWeightList") and len(w["dateWeightList"])>0:
            peso = w["dateWeightList"][0].get("weight")
    except: pass
    bb_max = s.get("bodyBatteryHighestValue")
    bb_min = s.get("bodyBatteryLowestValue")
    bb_recent = s.get("bodyBatteryMostRecentValue")
    if isinstance(bb_data, list) and bb_data:
        try:
            vals = [b.get("bodyBatteryValue") for b in bb_data if b.get("bodyBatteryValue") is not None]
            if vals:
                bb_max = max(vals) if bb_max is None else max(bb_max, max(vals))
                bb_min = min(vals) if bb_min is None else min(bb_min, min(vals))
                bb_recent = vals[-1]
        except: pass
    return {
        "data": giorno,
        "passi": s.get("totalSteps"),
        "passi_obiettivo": s.get("dailyStepGoal"),
        "calorie_totali": s.get("totalKilocalories"),
        "calorie_attive": s.get("activeKilocalories"),
        "calorie_bmr": s.get("bmrKilocalories"),
        "distanza_m": s.get("totalDistanceMeters"),
        "distanza_m_obiettivo": s.get("dailyDistanceGoal"),
        "fc_riposo": s.get("restingHeartRate"),
        "fc_max_giorno": s.get("maxHeartRate"),
        "fc_min_giorno": s.get("minHeartRate"),
        "fc_media_giorno": s.get("averageHeartRate"),
        "stress_medio": s.get("averageStressLevel") or (stress_data.get("avgStressLevel") if isinstance(stress_data, dict) else None),
        "stress_max": s.get("maxStressLevel") or (stress_data.get("maxStressLevel") if isinstance(stress_data, dict) else None),
        "body_battery_max": bb_max,
        "body_battery_min": bb_min,
        "body_battery_recent": bb_recent,
        "body_battery": bb_recent or bb_max,
        "sonno_totale_s": sonno.get("sleepTimeSeconds"),
        "sonno_profondo_s": sonno.get("deepSleepSeconds"),
        "sonno_leggero_s": sonno.get("lightSleepSeconds"),
        "sonno_rem_s": sonno.get("remSleepSeconds"),
        "sonno_veglia_s": sonno.get("awakeSleepSeconds"),
        "sonno_start": sonno.get("sleepStartTimestampGMT"),
        "sonno_end": sonno.get("sleepEndTimestampGMT"),
        "sonno_punteggio": punteggio.get("value"),
        "sonno_qualita": punteggio.get("qualifierKey"),
        "sonnellini_s": sonno.get("napTimeSeconds"),
        "hrv": hrv_val,
        "hrv_ms": hrv_val,
        "hrv_status": hrv_status,
        "respirazione_media_sveglio": (resp_data.get("avgWakingRespirationValue") if isinstance(resp_data, dict) else None),
        "respirazione_media_sonno": (resp_data.get("avgSleepRespirationValue") if isinstance(resp_data, dict) else None) or sonno.get("avgSleepRespirationValue"),
        "respirazione_min": resp_data.get("lowestRespirationValue") if isinstance(resp_data, dict) else None,
        "respirazione_max": resp_data.get("highestRespirationValue") if isinstance(resp_data, dict) else None,
        "spo2_media": (spo2_data.get("avgSpo2") if isinstance(spo2_data, dict) else None),
        "spo2_min": (spo2_data.get("lowestSpO2") if isinstance(spo2_data, dict) else None),
        "vo2max": vo2 or s.get("vo2Max"),
        "fitness_age": s.get("fitnessAge"),
        "training_status": training_status_label or s.get("trainingStatus"),
        "carico_acuto": acute_load or s.get("acuteLoad"),
        "carico_cronico": chronic_load,
        "readiness": readiness,
        "peso_kg": peso,
    }

def scarica_load_focus_ufficiale(api):
    print("\n--- Scarico Load Focus UFFICIALE ---")
    oggi = date.today().isoformat()
    try:
        ts = prova(api.get_training_status, oggi) or {}
        if ts:
            with open("training_status_raw.json","w",encoding="utf-8") as f:
                json.dump(ts, f, indent=2, ensure_ascii=False, default=str)

            balance_wrapper = ts.get("mostRecentTrainingLoadBalance") or {}
            dto_map = balance_wrapper.get("metricsTrainingLoadBalanceDTOMap") or {}

            entry = None
            for dev_id, data in dto_map.items():
                if data.get("primaryTrainingDevice"):
                    entry = data
                    break
            if not entry and dto_map:
                entry = list(dto_map.values())[0]

            print(f" ENTRY TROVATA: {entry}")

            if entry:
                basso = entry.get("monthlyLoadAerobicLow")
                alto = entry.get("monthlyLoadAerobicHigh")
                ana = entry.get("monthlyLoadAnaerobic")

                # Se Garmin ritorna None, non inventare
                if basso is None or alto is None or ana is None:
                    print(" ⚠ Load Focus incompleto da Garmin, mantengo vecchio")
                    return None

                result = {
                    "periodo": f"Ultimi 28 giorni al {oggi}",
                    "anaerobico": int(ana),
                    "aerobico_alto": int(alto),
                    "aerobico_basso": int(basso),
                    "w_ana": None,
                    "w_alto": None,
                    "w_basso": None,
                    "target_basso_min": entry.get("monthlyLoadAerobicLowTargetMin"),
                    "target_basso_max": entry.get("monthlyLoadAerobicLowTargetMax"),
                    "target_alto_min": entry.get("monthlyLoadAerobicHighTargetMin"),
                    "target_alto_max": entry.get("monthlyLoadAerobicHighTargetMax"),
                    "target_ana_min": entry.get("monthlyLoadAnaerobicTargetMin"),
                    "target_ana_max": entry.get("monthlyLoadAnaerobicTargetMax"),
                    "feedback": entry.get("trainingBalanceFeedbackPhrase"),
                    "messaggio": entry.get("trainingBalanceFeedbackPhrase") or entry.get("trainingStatusFeedbackPhrase"),
                    "fonte": "Garmin API VERO - metricsTrainingLoadBalanceDTOMap",
                    "timestamp": oggi,
                    "dettaglio": [
                        {"name": "Anaerobico", "value": int(ana)},
                        {"name": "Aerobico alto", "value": int(alto)},
                        {"name": "Aerobico basso", "value": int(basso)}
                    ]
                }
                with open("load_focus.json","w",encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f" ✓ Load Focus VERO: ANA={int(ana)} ALTO={int(alto)} BASSO={int(basso)}")
                return result

    except Exception as e:
        print(f" Errore parsing Load Focus: {e}")
        import traceback
        traceback.print_exc()

    print(" ⚠ Load Focus non trovato, nessun valore fisso inserito")
    return None

def main():
    api = accedi()
    oggi = date.today()
    vecchio_db = None
    if os.path.exists(FILE_DATABASE):
        print(f"Trovato {FILE_DATABASE} -> AGGIORNAMENTO")
        with open(FILE_DATABASE, "r", encoding="utf-8") as f: vecchio_db = json.load(f)
        GIORNI = GIORNI_AGGIORNAMENTO
        inizio = oggi - timedelta(days=GIORNI)
    else:
        print(f"Nessun DB -> PRIMO SCARICO")
        GIORNI = GIORNI_PRIMA_VOLTA
        inizio = oggi - timedelta(days=GIORNI)
    print(f"Periodo: da {inizio} a {oggi}")
    attivita_nuove = prova(api.get_activities_by_date, inizio.isoformat(), oggi.isoformat()) or []
    print("Attività nuove:", len(attivita_nuove))
    giorni_nuovi = []
    for i in range(GIORNI + 1):
        g = (inizio + timedelta(days=i)).isoformat()
        print(f" Giorno: {g}")
        giorni_nuovi.append(riassumi_giorno(api, g))

    load_focus = scarica_load_focus_ufficiale(api)

    if vecchio_db:
        mappa_giorni = {g["data"]: g for g in vecchio_db.get("giorni", [])}
        for g in giorni_nuovi: mappa_giorni[g["data"]] = g
        giorni_finali = sorted(mappa_giorni.values(), key=lambda x: x["data"])
        mappa_att = {a.get("raw",{}).get("activityId"): a for a in vecchio_db.get("attivita", [])}
        for a in [riassumi_attivita(x) for x in attivita_nuove]:
            aid = a.get("raw",{}).get("activityId")
            if aid: mappa_att[aid] = a
        attivita_finali = list(mappa_att.values())

        # Mantieni vecchio bilancio se nuovo è None
        bilancio_finale = load_focus if load_focus is not None else vecchio_db.get("bilancio_carico")

        database = {
            "periodo": {"da": giorni_finali[0]["data"], "a": giorni_finali[-1]["data"]},
            "attivita": attivita_finali,
            "giorni": giorni_finali,
            "load_focus": load_focus,
            "bilancio_carico": bilancio_finale
        }
    else:
        database = {
            "periodo": {"da": inizio.isoformat(), "a": oggi.isoformat()},
            "attivita": [riassumi_attivita(a) for a in attivita_nuove],
            "giorni": giorni_nuovi,
            "load_focus": load_focus,
            "bilancio_carico": load_focus
        }

    with open(FILE_DATABASE, "w", encoding="utf-8") as f: json.dump(database, f, ensure_ascii=False, indent=2)
    print("✔ Database salvato:", os.path.abspath(FILE_DATABASE))
    if database.get("bilancio_carico"):
        bc = database["bilancio_carico"]
        print(f"✔ Bilancio salvato: BASSO={bc.get('aerobico_basso')} ALTO={bc.get('aerobico_alto')} ANA={bc.get('anaerobico')}")
    else:
        print("⚠ Bilancio non disponibile, verrà mostrato come non disponibile in dashboard")
    input("\nPremi INVIO per chiudere...")

if __name__ == "__main__": main()
\n\ndef main_android(private_dir, email, password):\n    os.environ['ANDROID_PRIVATE']=private_dir\n    # sovrascrive accedi() per usare email/pass passati\n    import garminconnect\n    from pathlib import Path\n    Path(os.path.join(private_dir, '.garmin_tokens')).mkdir(exist_ok=True)\n    api=garminconnect.Garmin(email=email, password=password)\n    api.login(os.path.join(private_dir, '.garmin_tokens'))\n    # poi chiama main originale...\n    main()\n