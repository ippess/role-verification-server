import discord_api
from quart import Quart, redirect, Response, request, abort, render_template
from discord.ext.ipc import Client
import aiohttp
import os
import uvicorn
import logging
from dotenv import load_dotenv

load_dotenv()

app = Quart(__name__)
ipc = Client(host = "bot", secret_key=os.getenv("IPC_SECRET"))

@app.errorhandler(500)
async def bad(error):
    return error

@app.before_serving
async def create_client_session():
    app.aiohttp_session = aiohttp.ClientSession(raise_for_status=True)
    
@app.after_serving
async def close_client_session():
    await app.aiohttp_session.close()

@app.get("/")
async def root():
    return redirect("https://discord.gg/tradecentral")

@app.get("/linked-role")
async def linked_role():
    state, url = await discord_api.get_oauth_url()
    response = redirect(url)
    response.set_cookie('clientState', str(state))
    return response


@app.get("/discord-oauth-callback")
async def oauth():
    code = request.args.get('code')
    discord_state = request.args.get('state')
    client_state = request.cookies.get("clientState")
        
    if code is None or discord_state is None:
        return await render_template('fails.html', message='You should not be here!')
    if discord_state != client_state:
        return await render_template('fails.html', message='Unauthorized')

    try:
        tokens = await discord_api.get_oauth_tokens(session=app.aiohttp_session, code=code)
        data_me = await discord_api.get_user_data(session=app.aiohttp_session, tokens=tokens)
        connections = await discord_api.get_user_connections(session=app.aiohttp_session, tokens=tokens)
        guilds = await discord_api.get_user_guilds(session=app.aiohttp_session, tokens=tokens)
    except discord_api.DiscordAuthException:
        return await render_template('fails.html', message='Could not authorize with discord')
    except discord_api.DiscordAPIError:
        return await render_template('fails.html', message='Error while querying discord api"')
    except discord_api.HTTPException:
        return await render_template('fails.html', message=f'Error while querying discord api')

    response = await ipc.request(
        "resolve_metadata", 
        user_data=data_me, 
        connections=connections,
        guilds=guilds,
        user_agent=request.headers.get('User-Agent', "None"), 
        remote_addr=request.headers.get("X-Forwarded-For")
    )
    
    data = response.response

    if data is None:
        logging.error(f"Could not resolve metadata for {data_me['user']['id']}")
        return await render_template('fails.html', message='Could not resolve metadata')

    exception = data.get('exception', None)
    member = data.get('member', None)
    user = data.get('user', None)
    metadata = data.get('metadata', None)

    if not user:
        logging.error(f"User not found for {data_me['user']['id']}")
        return await render_template('fails.html', message='User not found.')
    if str(user['id']) != str(data_me['user']['id']):
        logging.error(f"User ID mismatch: {user['id']} != {data_me['user']['id']}")
        return await render_template('fails.html', message='User ID mismatch. Please try again or contact support.')
    if not member:
        logging.error(f"Member not found for {data_me['user']['id']}")
        return await render_template('fails.html', message='You need to join Trade Central first.')
    if exception:
        logging.error(f"Exception while resolving metadata for {data_me['user']['id']}: {exception}")
        return await render_template(
            'fails.html', message=f'Your account is not eligible for verification for the following reason: {exception}')
    if not metadata:
        logging.error(f"Metadata not found for {data_me['user']['id']}")
        return await render_template('fails.html', message='Metadata not found.')

    try:
        logging.info(f"Pushing metadata for {user['id']}: {metadata}")
        await discord_api.push_metadata(session=app.aiohttp_session, tokens=tokens, metadata=metadata)
    except exception as e:
        logging.error(f"Exception while pushing metadata for {user['id']}: {e}")
        return await render_template('fails.html', message='Exception while pushing metadata')
    
    return await render_template('success.html', name='Success')


if __name__ == "__main__":
    uvicorn.run("app:app", host="localhost", port=5005, log_level="info")