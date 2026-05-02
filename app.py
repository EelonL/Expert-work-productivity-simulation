
from __future__ import annotations

from dataclasses import asdict
from io import StringIO
from typing import Dict, List

import pandas as pd
import streamlit as st

from expert_work_abm import Environment, ExpertWorkSimulation


st.set_page_config(
    page_title="Asiantuntijatyön tuottavuuden simulaattori",
    page_icon="📈",
    layout="wide",
)


SCENARIOS: Dict[str, Environment] = {
    "Perustaso": Environment(),
    "Syvätyö / vähemmän keskeytyksiä": Environment(
        interruptions=0.15,
        goal_clarity=0.70,
    ),
    "Luova ja turvallinen työympäristö": Environment(
        autonomy=0.80,
        psychological_safety=0.80,
        feedback=0.70,
        external_knowledge=0.65,
        social_cohesion=0.70,
    ),
    "Ylikuormittunut organisaatio": Environment(
        workload=0.85,
        interruptions=0.60,
        uncertainty=0.60,
        goal_clarity=0.45,
        recovery=0.15,
    ),
}


SCENARIO_SHORT_NAMES = {
    "Perustaso": "Perustaso",
    "Syvätyö / vähemmän keskeytyksiä": "Syvätyö",
    "Luova ja turvallinen työympäristö": "Luova & turvallinen",
    "Ylikuormittunut organisaatio": "Ylikuormitus",
    "Oma skenaario": "Oma",
}


def chart_df(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Palauta kuvaajalle pivot-taulu lyhyillä sarakenimillä."""
    tmp = df.copy()
    tmp["skenaario_lyhyt"] = tmp["skenaario"].map(SCENARIO_SHORT_NAMES).fillna(tmp["skenaario"])
    return tmp.pivot(index="day", columns="skenaario_lyhyt", values=value_col)



PARAMETER_LABELS = {
    "autonomy": "Autonomia",
    "meaningfulness": "Työn merkityksellisyys",
    "feedback": "Palaute",
    "psychological_safety": "Psykologinen turvallisuus",
    "leadership_support": "Johtamisen tuki",
    "goal_clarity": "Tavoitteiden selkeys",
    "interruptions": "Keskeytykset",
    "workload": "Työmäärä",
    "uncertainty": "Epävarmuus / epäselvyys",
    "social_cohesion": "Sosiaalinen koheesio",
    "helping_norm": "Auttamisen normi",
    "external_knowledge": "Ulkoinen tieto",
    "coordination_noise": "Koordinaatiohäiriöt",
    "recovery": "Palautuminen",
}


PARAMETER_HELP = {
    "autonomy": "Kuinka paljon asiantuntijat voivat päättää työnsä tekemisen tavasta.",
    "meaningfulness": "Kuinka merkitykselliseksi työ koetaan.",
    "feedback": "Kuinka nopeasti ja laadukkaasti työstä saadaan palautetta.",
    "psychological_safety": "Kuinka turvallista on kysyä apua, tuoda esiin virheitä ja ehdottaa keskeneräisiä ajatuksia.",
    "leadership_support": "Kuinka paljon johto/esihenkilöt tukevat työn tekemistä ja kehittämistä.",
    "goal_clarity": "Kuinka selkeitä tavoitteet, prioriteetit ja odotukset ovat.",
    "interruptions": "Keskeytysten, kokoussirpaleisuuden ja huomion hajautumisen taso.",
    "workload": "Työmäärän ja kiireen taso.",
    "uncertainty": "Epävarmuus tehtävistä, vastuista, tiedosta tai tilanteesta.",
    "social_cohesion": "Luottamus ja yhteisöllisyys tiimissä.",
    "helping_norm": "Kuinka normaalia ja hyväksyttyä on auttaa muita.",
    "external_knowledge": "Kuinka paljon organisaatio saa ja hyödyntää ulkopuolista tietoa.",
    "coordination_noise": "Kommunikaatio- ja yhteensovitusongelmien määrä.",
    "recovery": "Palautumisen, taukojen ja energian uudistumisen taso.",
}


def env_to_dict(env: Environment) -> Dict[str, float]:
    return asdict(env)


def make_env(values: Dict[str, float]) -> Environment:
    valid = env_to_dict(Environment()).keys()
    return Environment(**{k: float(values[k]) for k in valid})


@st.cache_data(show_spinner=False)
def run_one_scenario(env_values: Dict[str, float], days: int, n_agents: int, seed: int) -> pd.DataFrame:
    env = make_env(env_values)
    sim = ExpertWorkSimulation(n_agents=n_agents, env=env, seed=seed)
    rows = sim.run(days=days)
    return pd.DataFrame(rows)


def run_named_scenarios(days: int, n_agents: int, seed: int) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for name, env in SCENARIOS.items():
        df = run_one_scenario(env_to_dict(env), days, n_agents, seed)
        df["skenaario"] = name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    last = (
        df.sort_values("day")
        .groupby("skenaario", as_index=False)
        .tail(1)
        .copy()
    )
    cols = [
        "skenaario",
        "overall_efficiency",
        "performance",
        "quality",
        "innovation",
        "learning",
        "rework",
        "burnout_risk",
        "lead_time_index",
    ]
    out = last[cols].copy()
    out = out.rename(
        columns={
            "skenaario": "Skenaario",
            "overall_efficiency": "Kokonaistehokkuus",
            "performance": "Tehtäväsuoritus",
            "quality": "Laatu",
            "innovation": "Innovaatio",
            "learning": "Oppiminen",
            "rework": "Uudelleentyö",
            "burnout_risk": "Burnout-riski",
            "lead_time_index": "Läpimenoaikaindeksi",
        }
    )
    return out


def metric_delta(custom_last: pd.Series, baseline_last: pd.Series, metric: str) -> float:
    return float(custom_last[metric] - baseline_last[metric])


st.title("Asiantuntijatyön tuottavuuden simulaattori")
st.caption(
    "Koulutuskäyttöön tarkoitettu agenttipohjainen hypoteesimalli. "
    "Muuttujat on skaalattu välille 0–1. Malli ei ole validoitu ennustemalli, vaan keskustelun ja skenaariotyöskentelyn väline."
)

with st.sidebar:
    st.header("Simulaation asetukset")
    mode = st.radio(
        "Mitä haluat tarkastella?",
        ["Valmiit skenaariot", "Oma skenaario"],
    )

    days = st.slider("Simulaation pituus, päivää", 30, 365, 160, step=10)
    n_agents = st.slider("Asiantuntijoiden määrä", 5, 200, 40, step=5)
    seed = st.number_input("Satunnaissiementä vastaava numero", value=42, step=1)

    st.divider()

    selected_base = st.selectbox("Lähtöskenaario", list(SCENARIOS.keys()))

    custom_values = env_to_dict(SCENARIOS[selected_base])

    if mode == "Oma skenaario":
        st.subheader("Muokkaa oman organisaation oletuksia")
        st.caption("0 = matala taso, 1 = korkea taso")

        for key, value in custom_values.copy().items():
            custom_values[key] = st.slider(
                PARAMETER_LABELS.get(key, key),
                min_value=0.0,
                max_value=1.0,
                value=float(value),
                step=0.05,
                help=PARAMETER_HELP.get(key, ""),
            )

tab_results, tab_parameters, tab_model = st.tabs(
    ["Tulokset", "Parametrit", "Mallin tulkinta"]
)

with tab_results:
    if mode == "Valmiit skenaariot":
        all_results = run_named_scenarios(days=days, n_agents=n_agents, seed=int(seed))

        st.subheader("Valmiiden skenaarioiden vertailu")
        summary = summarize(all_results)
        st.dataframe(summary.style.format(precision=3), use_container_width=True)

        with st.expander("Kuvaajien lyhenteet"):
            legend_df = pd.DataFrame(
                [{"Lyhenne": short, "Skenaario": full} for full, short in SCENARIO_SHORT_NAMES.items() if full in SCENARIOS]
            )
            st.dataframe(legend_df, hide_index=True, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            chart_data = chart_df(all_results, "overall_efficiency")
            st.line_chart(chart_data)
            st.caption("Kokonaistehokkuus: yhdistelmä suorituksesta, laadusta, oppimisesta, innovaatiosta, prosessitehokkuudesta, uudelleentyöstä ja burnout-riskistä.")

        with col2:
            chart_data = chart_df(all_results, "burnout_risk")
            st.line_chart(chart_data)
            st.caption("Burnout-riski: kuormituksen, keskeytysten ja epäselvyyden sekä autonomian ja tuen yhteisvaikutus.")

        col3, col4 = st.columns(2)

        with col3:
            chart_data = chart_df(all_results, "innovation")
            st.line_chart(chart_data)
            st.caption("Innovaatio syntyy mallissa luovan kapasiteetin, reflektiivisyyden ja tiedon jakamisen yhdistelmästä.")

        with col4:
            chart_data = chart_df(all_results, "lead_time_index")
            st.line_chart(chart_data)
            st.caption("Läpimenoaikaindeksi: pienempi arvo on parempi.")

        csv = all_results.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Lataa simulaatiodata CSV-muodossa",
            data=csv,
            file_name="asiantuntijatyon_simulaatio_valmiit_skenaariot.csv",
            mime="text/csv",
        )

    else:
        st.subheader("Oman skenaarion tulos")

        custom_df = run_one_scenario(custom_values, days, n_agents, int(seed))
        custom_df["skenaario"] = "Oma skenaario"

        baseline_df = run_one_scenario(env_to_dict(SCENARIOS["Perustaso"]), days, n_agents, int(seed))
        baseline_df["skenaario"] = "Perustaso"

        combined = pd.concat([baseline_df, custom_df], ignore_index=True)
        summary = summarize(combined)

        last_custom = custom_df.iloc[-1]
        last_baseline = baseline_df.iloc[-1]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "Kokonaistehokkuus",
            f"{last_custom['overall_efficiency']:.3f}",
            f"{metric_delta(last_custom, last_baseline, 'overall_efficiency'):+.3f} vs perustaso",
        )
        m2.metric(
            "Laatu",
            f"{last_custom['quality']:.3f}",
            f"{metric_delta(last_custom, last_baseline, 'quality'):+.3f}",
        )
        m3.metric(
            "Innovaatio",
            f"{last_custom['innovation']:.3f}",
            f"{metric_delta(last_custom, last_baseline, 'innovation'):+.3f}",
        )
        m4.metric(
            "Burnout-riski",
            f"{last_custom['burnout_risk']:.3f}",
            f"{metric_delta(last_custom, last_baseline, 'burnout_risk'):+.3f}",
            delta_color="inverse",
        )

        st.dataframe(summary.style.format(precision=3), use_container_width=True)

        with st.expander("Kuvaajien lyhenteet"):
            legend_df = pd.DataFrame(
                [
                    {"Lyhenne": "Perustaso", "Skenaario": "Perustaso"},
                    {"Lyhenne": "Oma", "Skenaario": "Oma skenaario"},
                ]
            )
            st.dataframe(legend_df, hide_index=True, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            st.line_chart(chart_df(combined, "overall_efficiency"))
            st.caption("Oma skenaario suhteessa perustasoon.")

        with col2:
            st.line_chart(chart_df(combined, "burnout_risk"))
            st.caption("Kuormitusriskin muutos.")

        col3, col4 = st.columns(2)

        with col3:
            st.line_chart(chart_df(combined, "innovation"))
            st.caption("Innovaatioindeksi.")

        with col4:
            st.line_chart(chart_df(combined, "lead_time_index"))
            st.caption("Läpimenoaikaindeksi, pienempi on parempi.")

        csv = combined.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Lataa oman skenaarion data CSV-muodossa",
            data=csv,
            file_name="asiantuntijatyon_simulaatio_oma_skenaario.csv",
            mime="text/csv",
        )

with tab_parameters:
    st.subheader("Skenaarioiden parametrien vertailu")

    parameter_df = pd.DataFrame(
        [
            {"Skenaario": name, **env_to_dict(env)}
            for name, env in SCENARIOS.items()
        ]
    )
    parameter_df = parameter_df.rename(columns=PARAMETER_LABELS)
    st.dataframe(parameter_df.style.format(precision=2), use_container_width=True)

    if mode == "Oma skenaario":
        st.subheader("Oman skenaarion parametrit")
        own_df = pd.DataFrame(
            [
                {
                    "Parametri": PARAMETER_LABELS.get(k, k),
                    "Arvo": v,
                    "Selitys": PARAMETER_HELP.get(k, ""),
                }
                for k, v in custom_values.items()
            ]
        )
        st.dataframe(own_df.style.format({"Arvo": "{:.2f}"}), use_container_width=True)

with tab_model:
    st.subheader("Miten mallia kannattaa tulkita?")

    st.markdown(
        """
        Tämä simulaattori on tarkoitettu **keskustelun, opetuksen ja skenaariotyöskentelyn välineeksi**.
        Se ei ennusta yksittäisen organisaation todellista tuottavuutta ilman kalibrointia.

        Mallin keskeinen ajatus on, että asiantuntijatyön tehokkuus ei synny vain nopeammasta suorittamisesta,
        vaan myös laadusta, oppimisesta, tiedon jakamisesta, luovuudesta, uudelleentyön vähenemisestä ja kuormituksen hallinnasta.

        **Tärkeimmät tulosmuuttujat**

        - **Kokonaistehokkuus**: yhdistelmä suoritusta, laatua, oppimista, innovaatiota ja prosessitehokkuutta.
        - **Laatu**: kasvaa osaamisen, keskittymisen, palautteen ja tiedonjaon mukana.
        - **Innovaatio**: syntyy luovan kapasiteetin, tiimin reflektiivisyyden ja tiedon jakamisen yhteisvaikutuksesta.
        - **Uudelleentyö**: kasvaa, jos laatu heikkenee, epävarmuus kasvaa tai koordinaatiohäiriöt lisääntyvät.
        - **Burnout-riski**: kasvaa kuormituksesta, keskeytyksistä ja epävarmuudesta; laskee autonomian ja johtamisen tuen mukana.
        - **Läpimenoaikaindeksi**: suhteellinen mittari; pienempi arvo tarkoittaa parempaa tilannetta.

        **Käyttö koulutuksessa**

        1. Aloittakaa valmiista skenaarioista.
        2. Keskustelkaa, mikä skenaario muistuttaa osallistujien organisaatiota.
        3. Muokatkaa oma skenaario.
        4. Verratkaa, mitkä tekijät näyttävät vaikuttavan eniten.
        5. Pohtikaa, mitkä muutokset olisivat organisaatiossa realistisia.
        """
    )

    with st.expander("Mallin keskeisiä laskentasääntöjä"):
        st.code(
            """
motivaatio =
  0.30*autonomia
+ 0.25*merkityksellisyys
+ 0.20*palaute
+ 0.25*työn_imu

kuormitus =
  0.40*työmäärä
+ 0.30*keskeytykset
+ 0.30*epävarmuus

luova_kapasiteetti =
  0.30*autonomia
+ 0.25*psykologinen_turvallisuus
+ 0.20*osaaminen
+ 0.15*energia
+ 0.10*ulkoinen_tieto

innovaatio =
  luova_kapasiteetti
* tiimin_reflektiivisyys
* tiedon_jakaminen

kokonaistehokkuus =
  0.35*tehtäväsuoritus
+ 0.25*laatu
+ 0.20*oppiminen
+ 0.20*innovaatio
+ 0.20*prosessitehokkuus
- 0.25*uudelleentyö
- 0.20*burnout_riski
            """,
            language="text",
        )
