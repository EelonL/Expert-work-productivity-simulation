"""
Agenttipohjainen asiantuntijatyön tehokkuusmalli.

Muuttujat on skaalattu välille 0..1.
Tämä on hypoteesimalli: kertoimet ovat alustavia ja tarkoitettu herkkyysanalyysiin,
ei validoiduksi kausaalimalliksi.

Aja:
    python expert_work_abm.py
"""

from __future__ import annotations

from dataclasses import dataclass
import random
import statistics
from typing import Dict, List

import matplotlib.pyplot as plt


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class Environment:
    autonomy: float = 0.65
    meaningfulness: float = 0.70
    feedback: float = 0.55
    psychological_safety: float = 0.60
    leadership_support: float = 0.55
    goal_clarity: float = 0.60
    interruptions: float = 0.35
    workload: float = 0.60
    uncertainty: float = 0.35
    social_cohesion: float = 0.55
    helping_norm: float = 0.55
    external_knowledge: float = 0.45
    coordination_noise: float = 0.30
    recovery: float = 0.25


@dataclass
class ExpertAgent:
    skill: float
    energy: float
    engagement: float
    motivation: float = 0.5
    learning: float = 0.5
    creative_capacity: float = 0.5
    focus: float = 0.5
    workload_stress: float = 0.5
    performance: float = 0.5
    quality: float = 0.5
    rework: float = 0.5
    burnout_risk: float = 0.2

    def step(self, env: Environment, team_reflexivity: float, knowledge_sharing: float) -> Dict[str, float]:
        """Päivitä yhden asiantuntija-agentin tila yhden päivän aikana."""

        noise = lambda scale=0.03: random.uniform(-scale, scale)

        self.motivation = clamp(
            0.30 * env.autonomy
            + 0.25 * env.meaningfulness
            + 0.20 * env.feedback
            + 0.25 * self.engagement
            + noise()
        )

        self.workload_stress = clamp(
            0.40 * env.workload
            + 0.30 * env.interruptions
            + 0.30 * env.uncertainty
            + noise()
        )

        self.energy = clamp(
            self.energy
            + env.recovery
            - 0.35 * self.workload_stress
            - 0.20 * env.interruptions
            + noise()
        )

        self.focus = clamp(
            self.energy * (1 - env.interruptions) * env.goal_clarity
            + noise()
        )

        self.learning = clamp(
            0.35 * env.feedback
            + 0.30 * knowledge_sharing
            + 0.20 * team_reflexivity
            + 0.15 * env.psychological_safety
            + noise()
        )

        self.creative_capacity = clamp(
            0.30 * env.autonomy
            + 0.25 * env.psychological_safety
            + 0.20 * self.skill
            + 0.15 * self.energy
            + 0.10 * env.external_knowledge
            + noise()
        )

        self.performance = clamp(
            0.30 * self.skill
            + 0.25 * self.focus
            + 0.20 * self.motivation
            + 0.15 * self.learning
            + 0.10 * self.creative_capacity
            - 0.25 * self.workload_stress
            + noise()
        )

        hurry = env.workload
        self.quality = clamp(
            0.35 * self.skill
            + 0.25 * self.focus
            + 0.20 * env.feedback
            + 0.20 * knowledge_sharing
            - 0.20 * hurry
            + noise()
        )

        self.rework = clamp(
            1 - self.quality
            + 0.30 * env.uncertainty
            + 0.20 * env.coordination_noise
            + noise()
        )

        self.engagement = clamp(
            self.engagement
            + 0.25 * env.autonomy
            + 0.20 * env.meaningfulness
            + 0.15 * env.feedback
            - 0.25 * self.workload_stress
            - 0.10
            + noise()
        )

        self.burnout_risk = clamp(
            0.40 * self.workload_stress
            + 0.25 * env.interruptions
            + 0.20 * env.uncertainty
            - 0.25 * env.autonomy
            - 0.15 * env.leadership_support
            + noise()
        )

        return {
            "performance": self.performance,
            "quality": self.quality,
            "rework": self.rework,
            "learning": self.learning,
            "creative_capacity": self.creative_capacity,
            "engagement": self.engagement,
            "burnout_risk": self.burnout_risk,
            "focus": self.focus,
            "energy": self.energy,
        }


class ExpertWorkSimulation:
    def __init__(self, n_agents: int = 30, env: Environment | None = None, seed: int = 42):
        random.seed(seed)
        self.env = env or Environment()
        self.agents = [
            ExpertAgent(
                skill=clamp(random.gauss(0.65, 0.12)),
                energy=clamp(random.gauss(0.70, 0.10)),
                engagement=clamp(random.gauss(0.60, 0.12)),
            )
            for _ in range(n_agents)
        ]
        self.process_efficiency = 0.50
        self.history: List[Dict[str, float]] = []

    def sharing_probability(self) -> float:
        return clamp(
            0.35 * self.env.psychological_safety
            + 0.25 * self.env.social_cohesion
            + 0.20 * self.env.leadership_support
            + 0.20 * self.env.helping_norm
        )

    def help_probability(self) -> float:
        task_difficulty = self.env.workload
        hurry = self.env.workload
        return clamp(
            0.40 * self.env.psychological_safety
            + 0.30 * task_difficulty
            + 0.20 * self.env.social_cohesion
            - 0.10 * hurry
        )

    def team_reflexivity(self) -> float:
        return clamp(
            0.45 * self.env.psychological_safety
            + 0.25 * self.env.leadership_support
            + 0.20 * self.env.goal_clarity
            + 0.10 * self.env.feedback
        )

    def step(self, day: int) -> Dict[str, float]:
        knowledge_sharing = self.sharing_probability()
        reflexivity = self.team_reflexivity()

        agent_results = [a.step(self.env, reflexivity, knowledge_sharing) for a in self.agents]

        avg = {
            key: statistics.mean(r[key] for r in agent_results)
            for key in agent_results[0]
        }

        innovation = clamp(avg["creative_capacity"] * reflexivity * knowledge_sharing)

        # Innovaatio ja oppiminen parantavat prosessia viiveellä.
        # Burnout ja uudelleentyö syövät hyötyä.
        self.process_efficiency = clamp(
            self.process_efficiency
            + 0.04 * innovation
            + 0.03 * avg["learning"]
            - 0.03 * avg["burnout_risk"]
            - 0.02 * avg["rework"]
        )

        overall_efficiency = clamp(
            0.35 * avg["performance"]
            + 0.25 * avg["quality"]
            + 0.20 * avg["learning"]
            + 0.20 * innovation
            + 0.20 * self.process_efficiency
            - 0.25 * avg["rework"]
            - 0.20 * avg["burnout_risk"]
        )

        lead_time_index = max(0.1, 1.0 / (0.20 + overall_efficiency) + avg["rework"])

        row = {
            "day": day,
            "overall_efficiency": overall_efficiency,
            "process_efficiency": self.process_efficiency,
            "innovation": innovation,
            "knowledge_sharing": knowledge_sharing,
            "team_reflexivity": reflexivity,
            "lead_time_index": lead_time_index,
            **avg,
        }

        self.history.append(row)
        return row

    def run(self, days: int = 120) -> List[Dict[str, float]]:
        for day in range(1, days + 1):
            self.step(day)
        return self.history


def run_scenarios(days: int = 160) -> Dict[str, List[Dict[str, float]]]:
    scenarios = {
        "baseline": Environment(),
        "deep_work": Environment(interruptions=0.15, goal_clarity=0.70),
        "creative_safe": Environment(
            autonomy=0.80,
            psychological_safety=0.80,
            feedback=0.70,
            external_knowledge=0.65,
            social_cohesion=0.70,
        ),
        "overload": Environment(
            workload=0.85,
            interruptions=0.60,
            uncertainty=0.60,
            goal_clarity=0.45,
            recovery=0.15,
        ),
    }

    results = {}
    for name, env in scenarios.items():
        sim = ExpertWorkSimulation(n_agents=40, env=env, seed=42)
        results[name] = sim.run(days=days)
    return results


def plot_results(results: Dict[str, List[Dict[str, float]]]) -> None:
    plt.figure(figsize=(10, 6))
    for name, rows in results.items():
        days = [r["day"] for r in rows]
        eff = [r["overall_efficiency"] for r in rows]
        plt.plot(days, eff, label=name)

    plt.xlabel("Päivä")
    plt.ylabel("Kokonaistehokkuus, 0–1")
    plt.title("Asiantuntijatyön tehokkuuden simulaatio")
    plt.legend()
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(10, 6))
    for name, rows in results.items():
        days = [r["day"] for r in rows]
        burnout = [r["burnout_risk"] for r in rows]
        plt.plot(days, burnout, label=name)

    plt.xlabel("Päivä")
    plt.ylabel("Burnout-riski, 0–1")
    plt.title("Kuormitusriskin kehitys eri skenaarioissa")
    plt.legend()
    plt.tight_layout()
    plt.show()


def print_summary(results: Dict[str, List[Dict[str, float]]]) -> None:
    print("\nLopputilanne skenaarioittain:\n")
    print(f"{'Skenaario':<15} {'Tehokkuus':>10} {'Laatu':>10} {'Innovaatio':>12} {'Uudelleentyö':>14} {'Burnout':>10}")
    print("-" * 78)

    for name, rows in results.items():
        last = rows[-1]
        print(
            f"{name:<15} "
            f"{last['overall_efficiency']:>10.3f} "
            f"{last['quality']:>10.3f} "
            f"{last['innovation']:>12.3f} "
            f"{last['rework']:>14.3f} "
            f"{last['burnout_risk']:>10.3f}"
        )


if __name__ == "__main__":
    results = run_scenarios(days=160)
    print_summary(results)
    plot_results(results)
