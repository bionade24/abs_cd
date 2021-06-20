import logging
import docker
from abs_cd.confighelper import Confighelper


logger = logging.getLogger(__name__)


class Connection():
    __docker_conn = None

    def __new__(self):
        if not self.__docker_conn:
            self.__docker_conn = docker.DockerClient(base_url=Confighelper()
                                                     .get_setting('DOCKER_SOCKET',
                                                                  'unix:///var/run/docker.sock'),
                                                     version='auto', tls=False)
            logger.debug("Successfully established connection")
        else:
            logger.debug("Connection to Docker socket already established")
        return self.__docker_conn
