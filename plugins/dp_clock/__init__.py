import threading
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

class Plugin:
    panel_id = "dp_clock"
    panel_label = "DP Clock"

    def __init__(self, ctx):
        self.ctx = ctx
        self._stop = threading.Event()
        self._cfg = ctx.load_plugin_config("dp_clock")

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            img = Image.new("RGB", (102, 102), (self._cfg["bg_b"], self._cfg["bg_g"], self._cfg["bg_r"]))
            draw = ImageDraw.Draw(img)

            now = datetime.now().strftime("%H:%M")
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=30)
            # bbox = draw.textbbox((0, 0), now, font=ImageFont.load_default())
            bbox = draw.textbbox((0, 0), now, font)

            x = (102 - bbox[2]) // 2
            y = (102 - bbox[3]) // 2

            draw.text((x, y), now, fill=(self._cfg["fg_b"], self._cfg["fg_g"], self._cfg["fg_r"]), font=font)

            self.ctx.push_displaypad_image(self._cfg["key"], img)
            self._stop.wait(1)
