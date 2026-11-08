"""Unit tests for stateful cross-run session memory store."""

from app.memory import SessionMemoryStore


def test_session_memory_read_write():
    """Verify storing and retrieving key facts in session memory."""
    store = SessionMemoryStore(db_path=":memory:")
    session_id = "session-100"

    store.write(session_id, "user_department", "Security")
    value = store.read(session_id, "user_department")

    assert value == "Security"


def test_session_memory_update():
    """Verify overwriting an existing fact updates the value."""
    store = SessionMemoryStore(db_path=":memory:")
    session_id = "session-100"

    store.write(session_id, "ticket_status", "Open")
    store.write(session_id, "ticket_status", "In-Progress")

    assert store.read(session_id, "ticket_status") == "In-Progress"


def test_session_isolation():
    """Verify different sessions have isolated memory namespaces."""
    store = SessionMemoryStore(db_path=":memory:")

    store.write("session-A", "user_role", "Admin")
    store.write("session-B", "user_role", "Guest")

    assert store.read("session-A", "user_role") == "Admin"
    assert store.read("session-B", "user_role") == "Guest"
    assert store.read("session-C", "user_role") is None


def test_session_list_and_clear():
    """Verify listing all facts and clearing a session."""
    store = SessionMemoryStore(db_path=":memory:")
    session_id = "session-cleanup"

    store.write(session_id, "k1", "v1")
    store.write(session_id, "k2", "v2")

    facts = store.list_facts(session_id)
    assert len(facts) == 2
    assert facts["k1"] == "v1"

    store.clear(session_id)
    assert len(store.list_facts(session_id)) == 0
