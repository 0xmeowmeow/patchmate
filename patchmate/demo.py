"""Generate questions for a handful of sample party guests with the real API.

    MODEL_API_KEY=... python -m patchmate.demo
"""

from .llm import MetaLLM
from .models import Connection, Guest
from .questions import questions_for_all

SAMPLE = [
    Guest("1", "Moth", curious_about="why some mushrooms glow in the dark",
          excited_about="night walks", nervous_about="not knowing anyone here",
          open_to={Connection.CONVERSATION, Connection.FRIENDSHIP}),
    Guest("2", "Lantern", curious_about="how old film cameras handle low light",
          excited_about="making a short horror film",
          open_to={Connection.CONVERSATION, Connection.COLLABORATION}),
    Guest("3", "Owl", curious_about="whether bats use echolocation to recognise each other",
          excited_about="learning the cello",
          open_to={Connection.CONVERSATION, Connection.ROMANCE}),
]


def main() -> None:
    for card in questions_for_all(MetaLLM(), SAMPLE):
        print(f"{card.pair}  {card.text}\n          host only: {card.why}\n")


if __name__ == "__main__":
    main()
