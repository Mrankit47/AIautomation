import asyncio
import httpx
from backend.config.settings import get_settings

async def diagnose():
    settings = get_settings()
    token = settings.instagram.access_token.get_secret_value()
    
    if not token:
        print("Error: INSTAGRAM__ACCESS_TOKEN is not set in .env")
        return
        
    print(f"Using access token starting with: {token[:10]}...")
    
    url = "https://graph.facebook.com/v19.0/me/accounts"
    params = {
        "fields": "name,id,instagram_business_account,category",
        "access_token": token
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("\nStep 0: Checking Token Permissions and User Details...")
            me_url = "https://graph.facebook.com/v19.0/me"
            me_params = {
                "fields": "name,id,permissions",
                "access_token": token
            }
            me_resp = await client.get(me_url, params=me_params)
            me_data = me_resp.json()
            if "error" in me_data:
                print(f"Error checking /me: {me_data['error']}")
            else:
                print(f"  Authenticated User: {me_data.get('name')} (ID: {me_data.get('id')})")
                perms = me_data.get("permissions", {}).get("data", [])
                active_perms = [p["permission"] for p in perms if p["status"] == "granted"]
                print(f"  Granted Permissions: {', '.join(active_perms)}")
                
            print("\nStep 1: Fetching your Facebook Pages and linked Instagram accounts...")
            resp = await client.get(url, params=params)
            data = resp.json()
            
            if "error" in data:
                print(f"\nAPI Error: {data['error']}")
                return
                
            pages = data.get("data", [])
            if not pages:
                print("\nNo Facebook Pages found linked to this access token.")
                print("Check list:")
                print("1. Jab aapne Graph API Explorer se token generate kiya, kya aapne use Facebook Page ka access diya tha?")
                print("2. Make sure check permissions like 'pages_show_list' and 'pages_read_engagement' are granted.")
                return
                
            print(f"\nFound {len(pages)} Facebook Page(s):")
            for page in pages:
                print(f"\n--- Page: {page.get('name')} (ID: {page.get('id')}) ---")
                ig_account = page.get("instagram_business_account")
                if ig_account:
                    print(f"  Instagram Business Account linked:")
                    print(f"    ID: {ig_account.get('id')}")
                    print(f"    Username/Name: {ig_account.get('username', 'N/A')}")
                    print(f"    -> Put this ID in your .env: INSTAGRAM__BUSINESS_ACCOUNT_ID={ig_account.get('id')}")
                else:
                    print("  No Instagram Business Account linked to this Facebook Page.")
                    print("  Check list:")
                    print("  1. Make sure your Instagram is a Business/Creator account (not personal).")
                    print("  2. Make sure it is linked to this Facebook Page under Page Settings -> Linked Accounts.")
                    
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(diagnose())
