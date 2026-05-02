# Asiantuntijatyön tuottavuuden simulaattori

Streamlit-sovellus agenttipohjaiseen asiantuntijatyön tuottavuuden skenaariosimulaatioon.

## Käyttö paikallisesti

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Julkaisu Streamlit Cloudissa

1. Luo GitHub-repositorio.
2. Vie tämän kansion tiedostot repositorion juureen:
   - `app.py`
   - `expert_work_abm.py`
   - `requirements.txt`
3. Mene Streamlit Cloudiin.
4. Valitse uusi appi GitHub-repositoriosta.
5. Main file path: `app.py`.

## Tulkinta

Malli on koulutus- ja skenaariotyökalu. Se ei ole validoitu ennustemalli.
Muuttujat ovat välillä 0–1 ja kertoimet alustavia.
