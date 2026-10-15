# Secure one-time OAuth authorization

Google requires the channel owner's personal login and consent. Do this on your
own trusted computer. Never paste client secrets, refresh tokens or passwords
into chat, repository files, issue comments or Actions logs.

1. In [Google Cloud Console](https://console.cloud.google.com/), select/create a
   project without a billing account. Enable **YouTube Data API v3** only; this
   API uses a free quota and does not require enabling paid services.
2. Configure Google Auth Platform branding/audience. For a personal channel,
   choose External. Add yourself as a test user if testing. Request only
   youtube.upload and youtube.readonly scopes.
3. Create an OAuth client of type **Desktop app**, download its JSON to your
   trusted computer outside your checkout, and keep it private.
4. For sustained automation, change the OAuth application's publishing status
   from **Testing** to **In production**. External Testing refresh tokens for
   YouTube scopes generally expire after seven days. In production does not
   publish any YouTube videos. Google may show an unverified-app warning or
   impose verification/user limits; follow Google's requirements. Do not evade
   organization restrictions.
5. Install Python dependencies and GitHub CLI, then sign in personally:

   ~~~sh
   gh auth login
   python -m pip install -r requirements.txt
   python scripts/oauth_setup.py --client-json /your/private/client_secret.json
   ~~~

6. In the browser, authorize the intended YouTube channel. The loopback callback
   stays on localhost. The helper verifies the channel and sends the four values
   directly to repository Actions Secrets over stdin. It does not print token
   values or save refresh tokens. If a secret write fails, rerun after correcting
   GitHub access; the factory requires all four values and a channel match.

The downloaded OAuth client file is Google's credential export; the factory
never copies it into the repository or artifacts. After setup, remove this local
export if unneeded and follow your device's secure storage practices.
The refresh token only survives in GitHub Secrets.

Optional scripting: create a free-tier key at [Google AI Studio](https://aistudio.google.com/)
using a project without billing. Store it with GitHub CLI:

~~~sh
gh secret set GEMINI_API_KEY --repo Nishat2001-hub/Nishat-info-hub-youtube
~~~

Enter it in the concealed prompt. Model availability/free quotas vary.
YouTube OAuth does not grant Gemini access; no AI key is needed for curated scripts.

Neither the connected repository tools nor this workspace can perform your
Google browser consent. The helper must run where your own browser can receive
the localhost callback. No passwords are requested by this project.
