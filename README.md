---
title: Pyth Price Poker
author: ApeWorX LTD.
keywords:
  - Pyth
  - Oracle
  - Trading
required_configuration:
  - PYTH_PRICEFEED_ADDRESS
  - PYTH_PRICEFEED_NAMES
---

# Overview

The Price Poker works with the [Pyth Network](https://pyth.network) and it's [Hermes Real-time API](https://hermes.pyth.network)
to obtain pricing updates and ensure that the oracle deployed on the given network is kept up to date.
This mimics the action of the Pyth ["price pusher"](https://docs.pyth.network/price-feeds/schedule-price-updates/using-scheduler)
scheduler using Silverback.

## Configuration

### Pyth Configuration

These variables are required to set up operation of the price pusher

#### `PYTH_PRICEFEED_ADDRESS`

_required_

The address of the Pyth `PriceFeedProxy` contract which should be used to update.

#### `PYTH_PRICEFEED_NAMES`

_required_

1 or more named pricefeeds to fetch from the Hermes API and update on chain, if update thresholds are not met.
These should be in their human readable form by symbol, e.g. "ETH/USD" or "BTC/USD".
Multiple should be provided via comma-separated list e.g. `PYTH_PRICEFEED_NAMES=ETH/USD,BTC/USD`.

### Update Threshold Configuration

These variables configure when a pricefeed update should take place.

#### `HEARTBEAT_TIMEOUT`

_optional_

Number of seconds before an update is considered "stable".
When stale, the bot will update the price on-chain.
Defaults to 1 hour.

#### `PRICE_CHANGE_THESHOLD`

_optional_

Percentage change in latest price vs. last on-chain update which should trigger an on-chain update.
Defaults to 5%.

#### `PYTH_UPDATE_CRON`

_optional_

The frequency at which the pricefeed check task should run.
Defaults to every minute.

## Metrics

### `{PRICEFEED_NAME}`

Metric(s) that track the current on-chain value of each price feed as it is updated.
