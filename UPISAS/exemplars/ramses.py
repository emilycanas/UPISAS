from UPISAS.exemplar import Exemplar

# ADDED AFTERWARDS:
# UPISAS/exemplars/ramses.py points UPISAS at http://localhost:50000 and starts the scenario with these settings. 
# Download the image first with docker pull, and use your own architecture in its name.

class DemoExemplar(Exemplar):
    """
    A class which encapsulates a self-adaptive exemplar run in a docker container.
    """
    def __init__(self, auto_start=False, container_name="upisas-demo"):
        docker_config = {
            "name": "simulation-scenario",
            "image": "giamburrasca/scenario1:arm64",
            "network": "ramses-sas-net",
            "environment": {
                "ADAPT": "0",
                "FAILURE_INJECTION_1_START": "120",
            },
        }

        super().__init__("http://localhost:3000", docker_config, auto_start)

    def start_run(self, app):
        self.exemplar_container.exec_run(cmd = f' sh -c "cd /usr/src/app && node {app}" ', detach=True)
