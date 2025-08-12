import os
from datetime import UTC, datetime, timedelta

import httpx
from ape import Contract
from ape.types import HexBytes
from ape_ethereum import multicall
from silverback import SilverbackBot

HEARTBEAT_TIMEOUT = timedelta(seconds=int(os.environ.get("HEARTBEAT_TIMEOUT", "3600")))
PRICE_CHANGE_THRESHOLD = float(os.environ.get("PRICE_CHANGE_THESHOLD", "5.0")) / 100

bot = SilverbackBot()
pyth = Contract(os.environ["PYTH_PRICEFEED_ADDRESS"])
pyth_api = httpx.AsyncClient(
    base_url="https://hermes.pyth.network/v2",
    transport=httpx.AsyncHTTPTransport(retries=10),
)

if (PRICEFEED_NAMES := os.environ.get("PYTH_PRICEFEED_NAMES", "").split(",")) == [""]:
    raise RuntimeError("Must specify at least one pricefeed via PYTH_PRICEFEED_NAMES=")


async def get_pricefeed_id(name: str) -> HexBytes:
    result = await pyth_api.get(
        "/price_feeds", params=dict(query=name, asset_type="crypto")
    )
    result.raise_for_status()

    for item in result.json():
        if item["attributes"]["display_symbol"] == name:
            return HexBytes(item["id"])

    raise RuntimeError(f"Could not find feed for {name}")


@bot.on_startup()
async def setup_caches(_):
    call = multicall.Call()
    bot.state.pricefeeds = {
        await get_pricefeed_id(name): name for name in PRICEFEED_NAMES
    }

    for feed_id in bot.state.pricefeeds:
        call.add(pyth.getPriceUnsafe, feed_id)

    bot.state.last_update = dict()
    bot.state.last_price = dict()
    for feed_id, price_struct in zip(bot.state.pricefeeds, call()):
        bot.state.last_update[feed_id] = datetime.fromtimestamp(
            price_struct.publishTime, tz=UTC
        )
        bot.state.last_price[feed_id] = price_struct.price


@bot.on_(pyth.PriceFeedUpdate)
async def pricefeed_updated(log):
    if (feed_id := HexBytes(log.id)) in bot.state.pricefeeds:
        bot.state.last_update[feed_id] = datetime.fromtimestamp(log.publishTime, tz=UTC)
        bot.state.last_price[feed_id] = log.price
        return {bot.state.pricefeeds[feed_id]: log.price}


async def get_latest_price(feed_id: HexBytes) -> int:
    result = await pyth_api.get(
        "/updates/price/latest",
        params={"ids[]": "0x" + feed_id.hex()},
    )
    result.raise_for_status()
    data = result.json()
    return int(data["parsed"][0]["price"]["price"])


@bot.cron(os.environ.get("PYTH_UPDATE_CRON", "* * * * *"))
async def check_and_update_pricefeeds(time: datetime):
    pricefeeds_to_update = [
        "0x" + feed_id.hex()
        for feed_id in bot.state.pricefeeds
        if (time - bot.state.last_update[feed_id]) > HEARTBEAT_TIMEOUT
        or (
            abs(await get_latest_price(feed_id) - bot.state.last_price[feed_id])
            / bot.state.last_price[feed_id]
        )
        > PRICE_CHANGE_THRESHOLD
    ]

    if not pricefeeds_to_update:
        return

    result = await pyth_api.get(
        "/updates/price/latest",
        params={"ids[]": pricefeeds_to_update},
    )
    result.raise_for_status()
    data = result.json()
    encoded_updates = list(map(HexBytes, data["binary"]["data"]))

    # TODO: if no `bot.signer`, send alert

    pyth.updatePriceFeeds(
        encoded_updates,
        sender=bot.signer,
        required_confirmations=0,
        value=pyth.getUpdateFee(encoded_updates),
    )
