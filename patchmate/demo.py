"""Generate questions for a handful of sample party guests with the real API.

    MODEL_API_KEY=... python -m patchmate.demo
"""

from .llm import MetaLLM
from .models import Connection, Guest
from .questions import questions_for_all
from .quests import quests_for_all as quests

SAMPLE = [
    Guest("1", "Moth", curious_about="why some mushrooms glow in the dark",
          excited_about="night walks", nervous_about="not knowing anyone here",
          find_me_for="just got back from two weeks in Japan",
          open_to={Connection.CONVERSATION, Connection.FRIENDSHIP}),
    Guest("2", "Lantern", curious_about="how old film cameras handle low light",
          excited_about="making a short horror film", find_me_for="I keep bees on my roof",
          open_to={Connection.CONVERSATION, Connection.COLLABORATION}),
    Guest("3", "Owl", curious_about="whether bats use echolocation to recognise each other",
          excited_about="learning the cello",
          open_to={Connection.CONVERSATION, Connection.ROMANCE}),
]


def main() -> None:
    for card in questions_for_all(MetaLLM(), SAMPLE):
        print(f"{card.pair}  {card.text}\n          host only: {card.why}\n")
    names = {g.id: g.nickname for g in SAMPLE}
    llm = MetaLLM()
    for q in quests(llm, SAMPLE):
        print(f"quest for {names[q.seeker]}: {q.clue}   ({names[q.target]} holds the word '{q.word}')")


if __name__ == "__main__":
    main()
