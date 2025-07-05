from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm


class Spawner:
    def __init__(self, config):
        self.config = config
        self.kill_flag = False

    def spawn_single(self, progress=True):
        if progress:
            bar = tqdm.tqdm
        else:
            bar = lambda a, **kwargs: a
        try:
            executor = ThreadPoolExecutor(max_workers=self.config["num_threads"])
            drops = []
            futures = [
                executor.submit(self.config.pick_drop, i, self)
                for i in range(self.config["num_drops"])
            ]
            for future in bar(
                as_completed(futures, timeout=self.config.get("global_timeout", 7200)),
                total=len(futures),
            ):
                try:
                    res = future.result(timeout=self.config.get("drop_timeout", 5))
                    if not res:
                        continue
                    drop = res
                except TimeoutError:
                    continue
                drops.append(drop.as_dict())
        except TimeoutError:
            pass
        print(f"importing {len(drops)} drops")
        self.config.client.import_drops(
            drops,
            self.config["map_id"],
            "map",
            self.config.get("import_method", "merge"),
        )
        print("killing")
        self.kill_flag = True
        executor.shutdown(wait=False)
        for future in futures:
            future.cancel()

    def spawn(self, progress=True):
        if self.config["map_type"] == "single":
            self.spawn_single(progress)
