"""
意图识别模块单元测试
"""

import pytest
import yaml
from pathlib import Path

from app.agent import IntentType, create_initial_state
from app.agent.nodes import parse_intent_response, validate_intent, CONFIDENCE_THRESHOLD


class TestParseIntentResponse:
    """JSON 解析测试"""

    def test_parse_valid_json(self):
        """测试解析有效的 JSON"""
        content = '{"intent": "fitness_consult", "confidence": 0.95, "entities": {"body_part": "腹肌"}}'
        result = parse_intent_response(content)

        assert result["intent"] == "fitness_consult"
        assert result["confidence"] == 0.95
        assert result["entities"]["body_part"] == "腹肌"

    def test_parse_json_with_extra_text(self):
        """测试解析带额外文本的 JSON"""
        content = '根据分析，结果是 {"intent": "plan_request", "confidence": 0.98, "entities": {}}'
        result = parse_intent_response(content)

        assert result["intent"] == "plan_request"
        assert result["confidence"] == 0.98

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        content = '这不是一个有效的 JSON'
        result = parse_intent_response(content)

        assert result["intent"] == "unknown"
        assert result["confidence"] == 0.5  # 默认值

    def test_parse_partial_json(self):
        """测试解析部分 JSON（正则提取）"""
        content = 'intent: "chitchat", confidence: 0.9'
        result = parse_intent_response(content)

        assert result["intent"] == "chitchat"

    def test_parse_missing_confidence(self):
        """测试缺少置信度字段"""
        content = '{"intent": "nutrition_consult", "entities": {}}'
        result = parse_intent_response(content)

        assert result["intent"] == "nutrition_consult"
        assert result["confidence"] == 0.5  # 默认值


class TestValidateIntent:
    """意图验证测试"""

    def test_validate_valid_intent(self):
        """测试验证有效的意图"""
        assert validate_intent("fitness_consult") == "fitness_consult"
        assert validate_intent("plan_request") == "plan_request"
        assert validate_intent("body_metrics") == "body_metrics"
        assert validate_intent("nutrition_consult") == "nutrition_consult"
        assert validate_intent("exercise_guide") == "exercise_guide"
        assert validate_intent("data_record") == "data_record"
        assert validate_intent("chitchat") == "chitchat"
        assert validate_intent("unknown") == "unknown"

    def test_validate_invalid_intent(self):
        """测试验证无效的意图"""
        assert validate_intent("invalid_intent") == "unknown"
        assert validate_intent("random_string") == "unknown"

    def test_validate_intent_case_insensitive(self):
        """测试大小写不敏感"""
        assert validate_intent("FITNESS_CONSULT") == "fitness_consult"
        assert validate_intent("Plan_Request") == "plan_request"


class TestConfidenceThreshold:
    """置信度阈值测试"""

    def test_threshold_value(self):
        """测试阈值设置"""
        assert CONFIDENCE_THRESHOLD == 0.5

    def test_low_confidence_should_be_unknown(self):
        """测试低置信度应标记为 unknown"""
        # 在 intent_node 中会检查置信度
        # 这里只验证阈值本身
        low_confidence = 0.3
        assert low_confidence < CONFIDENCE_THRESHOLD

        high_confidence = 0.8
        assert high_confidence >= CONFIDENCE_THRESHOLD


class TestIntentTestCases:
    """测试集验证"""

    @pytest.fixture
    def test_cases(self):
        """加载测试集"""
        test_file = Path(__file__).parent / "fixtures" / "intent_test_cases.yaml"
        with open(test_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data["test_cases"]

    def test_all_intent_types_covered(self, test_cases):
        """测试覆盖所有意图类型"""
        covered_intents = {tc["expected_intent"] for tc in test_cases}
        required_intents = {e.value for e in IntentType}

        # 检查是否覆盖所有意图
        for intent in required_intents:
            assert intent in covered_intents, f"测试集缺少意图类型: {intent}"

    def test_test_cases_valid(self, test_cases):
        """测试测试集的有效性"""
        valid_intents = {e.value for e in IntentType}

        for tc in test_cases:
            assert "query" in tc, "测试用例缺少 query 字段"
            assert "expected_intent" in tc, "测试用例缺少 expected_intent 字段"
            assert tc["expected_intent"] in valid_intents, f"无效的意图类型: {tc['expected_intent']}"

    def test_test_cases_count(self, test_cases):
        """测试用例数量"""
        # 每种意图至少有 2 个测试用例
        intent_counts = {}
        for tc in test_cases:
            intent = tc["expected_intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        for intent, count in intent_counts.items():
            assert count >= 2, f"意图 {intent} 的测试用例不足 2 个"


class TestIntentNodeIntegration:
    """意图识别集成测试（需要真实 API）"""

    @pytest.mark.skip(reason="需要真实 API Key，手动测试时取消跳过")
    @pytest.mark.asyncio
    async def test_intent_node_real_api(self):
        """测试真实 API 调用"""
        from app.agent.nodes import intent_node

        state = create_initial_state("怎么练腹肌最快", "test-session")
        result = await intent_node(state)

        assert result["intent"] == "fitness_consult"
        assert result["intent_confidence"] >= CONFIDENCE_THRESHOLD

    @pytest.mark.skip(reason="需要真实 API Key，手动测试时取消跳过")
    @pytest.mark.asyncio
    async def test_intent_node_plan_request(self):
        """测试训练计划请求识别"""
        from app.agent.nodes import intent_node

        state = create_initial_state("帮我制定一个减脂计划", "test-session")
        result = await intent_node(state)

        assert result["intent"] == "plan_request"

    @pytest.mark.skip(reason="需要真实 API Key，手动测试时取消跳过")
    @pytest.mark.asyncio
    async def test_intent_node_low_confidence(self):
        """测试低置信度输入"""
        from app.agent.nodes import intent_node

        state = create_initial_state("那个...就是...健身", "test-session")
        result = await intent_node(state)

        # 置信度低于阈值时应为 unknown
        if result["intent_confidence"] < CONFIDENCE_THRESHOLD:
            assert result["intent"] == "unknown"
