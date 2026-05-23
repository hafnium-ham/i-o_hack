import asyncio
from rocketride import RocketRideClient

async with RocketRideClient(uri="http://localhost:5565", auth="your-chosen-key") as client:
    token = (await client.use(filepath="pipeline.pipe"))["token"]
    result = await client.send(token, "Summarize this document")
    print(result["data"])