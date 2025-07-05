from .countries import country_from_position

KEYS = ("id", "style", "lat", "lng", "code", "panoId", "subCode")


class Drop:
    def __init__(
        self,
        lat,
        lon,
        code=None,
        pano_id=None,
        sub_code=None,
        style="streetview",
        id=1,
        **kwargs
    ):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.code = code or country_from_position(lat, lon)
        self.pano_id = pano_id
        self.sub_code = sub_code
        self.style = style
        self.kwargs = kwargs

    def as_dict(self):
        return {
            **{
                k: v
                for k, v in zip(
                    KEYS,
                    (
                        self.id,
                        self.style,
                        self.lat,
                        self.lon,
                        self.code,
                        self.pano_id,
                        self.sub_code,
                    ),
                )
                if v is not None
            },
            **self.kwargs,
        }
