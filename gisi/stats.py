from collections import OrderedDict
from datetime import datetime
from io import BytesIO

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

plt.style.use("fivethirtyeight")


class Statistics:
    def __init__(self, bot):
        self.bot = bot
        self.storage = bot.mongo_db.statistics

    async def trigger_event(self, event):
        await self.storage.update_one({"_id": event}, {"$push": {"occurrences": datetime.utcnow()}}, upsert=True)

    async def count_events(self, event, timestep=86400, start=None, end=None):
        occurrences = OrderedDict()
        result = await self.storage.find_one(event)
        raw_occurrences = result["occurrences"]
        for raw_occurrence in raw_occurrences:
            if start and raw_occurrence < start:
                continue
            if end and raw_occurrence > end:
                break
            target_date = datetime.fromtimestamp(timestep * (raw_occurrence.timestamp() // timestep))
            occurrences[target_date] = occurrences.get(target_date, 0) + 1
        return occurrences

    async def draw(self, occurrences):
        x, y = zip(*occurrences)
        plt.close()
        fig, ax = plt.subplots()
        ax.bar(x, y, width=.0005)

        locator = mdates.AutoDateLocator(interval_multiples=True)
        formatter = mdates.AutoDateFormatter(locator)
        formatter.scaled[1 / mdates.MINUTES_PER_DAY] = "%H:%M"
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        fig.autofmt_xdate()
        fig.tight_layout(pad=1.2)

        img = BytesIO()
        fig.savefig(img, format="png")
        img.seek(0)
        return img

    async def on_message(self, message):
        await self.trigger_event("on_message")

    async def on_command(self, ctx):
        await self.trigger_event("on_command")

    async def on_error(self, event_method, *args, **kwargs):
        await self.trigger_event("on_error")

    async def on_command_error(self, context, exception):
        await self.trigger_event("on_command_error")
