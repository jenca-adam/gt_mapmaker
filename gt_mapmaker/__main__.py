from . import config, spawner

config = config.Config()
spawner.Spawner(config).spawn()
