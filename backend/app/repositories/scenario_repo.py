from app.schemas.scenario import ScenarioItem, ScenariosResponse

# Built-in mock scenarios so the app is demoable before EmoBench is loaded.
# TODO(P18-DATA-1/2): read scenarios from the scenario_items + questions tables instead
# (join + task_type/dimension filters + real total), falling back to these when empty.
MOCK_SCENARIOS = [
    ScenarioItem(
        question_id="q_regina_001",
        scenario_item_id="s_regina_001",
        task_type="EU",
        dimension="emotion_cause",
        subject="Regina",
        scenario=(
            "Regina's best friend recently broke up with her longtime partner and is "
            "texting Regina in the middle of the night expressing feelings of loneliness."
        ),
        question_text="What should Regina do?",
        choices={
            "A": "Ignore the texts and continue sleeping",
            "B": "Tell her friend to seek professional help",
            "C": "Stay up and lend a listening ear",
            "D": "Suggest her friend find a new partner",
        },
        label="C",
    ),
    ScenarioItem(
        question_id="q_omar_001",
        scenario_item_id="s_omar_001",
        task_type="EA",
        dimension="emotion_regulation",
        subject="Omar",
        scenario=(
            "Omar received harsh feedback on a presentation and feels embarrassed before "
            "his next meeting."
        ),
        question_text="What is the most emotionally constructive response?",
        choices={
            "A": "Avoid the meeting completely",
            "B": "Pause, review the feedback, and prepare one improvement",
            "C": "Blame the audience for misunderstanding",
            "D": "Send an angry message to his manager",
        },
        label="B",
    ),
]


class ScenarioRepository:
    def list_scenarios(
        self,
        task_type: str | None,
        dimension: str | None,
        limit: int,
        offset: int,
    ) -> ScenariosResponse:
        items = MOCK_SCENARIOS
        if task_type:
            items = [item for item in items if item.task_type == task_type]
        if dimension:
            items = [item for item in items if item.dimension == dimension]
        return ScenariosResponse(items=items[offset : offset + limit], total=len(items))
