import asyncio

from voice_benchmark.orchestrator import run_benchmark


def test_mock_benchmark_run():
    result = asyncio.run(run_benchmark("mock", calls=3, mode="mock"))
    assert result.total_calls == 3
    assert result.stack == "mock"
    for call in result.calls:
        assert call.turn_latencies or not call.success


def test_compare_reference_stacks():
    from voice_benchmark.orchestrator import compare_stacks

    results = asyncio.run(
        compare_stacks(["vapi", "retell"], calls=2, mode="mock")
    )
    assert len(results) == 2
    assert {r.stack for r in results} == {"vapi", "retell"}
