import pytest

from backend.models.skill_config import SkillConfig
from backend.repositories.skill_config_storage import SkillConfigStorage
from tests.testing_utils import TEST_USER_ID


@pytest.fixture
def skill_data():
    return {
        "id": "skill1",
        "user_id": TEST_USER_ID,
        "title": "Example Skill",
        "content": 'print("Hello, World!")',
        "timestamp": "2024-05-05T00:14:57.487901+00:00",
    }


@pytest.fixture
@pytest.mark.usefixtures("mock_firestore_client")
def mock_storage():
    return SkillConfigStorage()


def test_load_skill_config_by_user_id(mock_storage, mock_firestore_client, skill_data):
    mock_firestore_client.setup_mock_data("skill_configs", "skill1", skill_data)

    loaded_skill_configs = mock_storage.load_by_user_id(skill_data["user_id"])

    expected_skill_config = SkillConfig.model_validate(skill_data)
    assert loaded_skill_configs == [expected_skill_config]


def test_load_skill_config_by_id(mock_storage, mock_firestore_client, skill_data):
    mock_firestore_client.setup_mock_data("skill_configs", "skill1", skill_data)

    loaded_skill_config = mock_storage.load_by_id(skill_data["id"])

    expected_skill_config = SkillConfig.model_validate(skill_data)
    assert loaded_skill_config == expected_skill_config


def test_save_new_skill_config(mock_storage, mock_firestore_client, skill_data):
    # Test case for creating a new skill config
    mock_firestore_client.setup_mock_data("skill_configs", "skill2", skill_data)

    new_skill_data = skill_data.copy()
    del new_skill_data["id"]  # Simulate a new skill without an id
    skill_config = SkillConfig(**new_skill_data)

    skill_id = mock_storage.save(skill_config)

    assert skill_id == "skill2"

    serialized_data = skill_config.model_dump()
    assert mock_firestore_client.to_dict() == serialized_data
    assert skill_config.id == "skill2"


def test_update_existing_skill_config(mock_storage, mock_firestore_client, skill_data):
    # Test case for updating an existing skill config
    mock_firestore_client.setup_mock_data("skill_configs", "skill1", skill_data)

    skill_config = SkillConfig(**skill_data)
    mock_storage.save(skill_config)

    serialized_data = skill_config.model_dump()
    assert mock_firestore_client.to_dict() == serialized_data
    assert skill_config.id == skill_data["id"]


def test_load_skill_config_by_titles(mock_storage, mock_firestore_client, skill_data):
    # Setup multiple skills in the mock database
    titles = ["Example Skill", "Another Skill"]
    skill_data2 = skill_data.copy()
    skill_data2["id"] = "skill2"
    skill_data2["title"] = titles[1]

    mock_firestore_client.setup_mock_data("skill_configs", "skill1", skill_data)
    mock_firestore_client.setup_mock_data("skill_configs", "skill2", skill_data2)

    loaded_skill_configs = mock_storage.load_by_titles(titles)

    expected_skill_config1 = SkillConfig.model_validate(skill_data)
    expected_skill_config2 = SkillConfig.model_validate(skill_data2)

    # Assert both skills are returned and in any order
    assert len(loaded_skill_configs) == 2
    assert expected_skill_config1 in loaded_skill_configs
    assert expected_skill_config2 in loaded_skill_configs


def test_load_skill_config_by_titles_exceeds_max_size(mock_storage):
    titles = ["Example Skill"] * 11

    with pytest.raises(ValueError) as excinfo:
        mock_storage._load_by_titles(titles)

    assert "Titles list exceeds the maximum size of 10 for an 'in' query in Firestore." in str(excinfo.value)


def test_delete_skill_config(mock_storage, mock_firestore_client, skill_data):
    mock_firestore_client.setup_mock_data("skill_configs", "skill1", skill_data)

    mock_storage.delete(skill_data["id"])

    assert mock_firestore_client.to_dict() == {}
