import platform

from UPISAS.exemplar import Exemplar

# arm64 on Apple Silicon Macs, amd64 on Intel/AMD (Windows, Linux, Intel Macs)
ARCH = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "amd64"

# Every scenario we can run: which image, which settings, and how long a run lasts.
# ADAPT=0 always: RAMSES's own controller must stay off, our UPISAS strategy adapts.
# The custom images are built locally (see custom-scenario/), so they need no ARCH.
SCENARIOS = {
    "default": {
        "image": f"giamburrasca/scenario1:{ARCH}",
        "environment": {"ADAPT": "0", "FAILURE_INJECTION_1_START": "120"},
        "run_seconds": 300,
    },
    "custom1": {
        "image": "custom-scenario1",
        "environment": {"ADAPT": "0"},
        "run_seconds": 600,
    },
    "custom2": {
        "image": "custom-scenario2",
        "environment": {"ADAPT": "0"},
        "run_seconds": 600,
    },
}


class RAMSES(Exemplar):
    """
    A class which encapsulates a self-adaptive exemplar run in a docker container.
    """
    def __init__(self, scenario="default", auto_start=False):
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario: {scenario}")
        settings = SCENARIOS[scenario]

        docker_config = {
            "name": "simulation-scenario",
            "image": settings["image"],
            "network": "ramses-sas-net",
            "environment": settings["environment"],
        }
        # The runner reads this to know how long to run
        self.run_seconds = settings["run_seconds"]

        super().__init__("http://localhost:50000", docker_config, auto_start)

    def start_run(self):
        self.start_container()
