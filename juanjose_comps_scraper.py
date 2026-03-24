import requests

def get_recent_comps(zip_code):
    """
    Searches for recently sold homes in a specific ZIP code
    using Juan's IDX Broker map search API.
    """
    idx_base_url = "https://juanjoseelizondo.idxbroker.com/idx/api/widgets/mapsearch/results"
    
    # We attempt to find sold listings in the zip code
    params = {
        "idxID": "d337",
        "ccz": "zipcode",
        "statusCategory": "sold",
        "zipcode": zip_code,
        "coID": "d337"
    }
    
    headers = {
        "referer": "https://juanjoseelizondo.com/",
        "accept": "application/json, text/plain, */*",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(idx_base_url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            sold_prices = []
            sqfts = []
            
            listings = data.get('properties', []) if isinstance(data, dict) else data
            
            def parse_listings(lsts):
                for listing in lsts:
                    try:
                        price = float(str(listing.get('price', '0')).replace(',', '').replace('$', ''))
                        sqft = float(str(listing.get('sqFt', '0')).replace(',', ''))
                        if price > 0 and sqft > 0:
                            sold_prices.append(price)
                            sqfts.append(sqft)
                    except ValueError:
                        continue
                        
            parse_listings(listings)
            
            # Fallback to active comps if sold data is unavailable behind IDX broker
            if not sold_prices:
                params['statusCategory'] = 'active'
                response = requests.get(idx_base_url, params=params, headers=headers)
                data = response.json()
                listings = data.get('properties', []) if isinstance(data, dict) else data
                parse_listings(listings)

            
            # Connect to math engine
            from investor_osint_engine import InvestorIntelligenceOSINT
            osint = InvestorIntelligenceOSINT()
            # If we had a target house (e.g. 3708 S Apex St with 1472 sqft priced at 269900)
            target_price = 269900
            target_sqft = 1472
            analysis = osint.calculate_comps_and_ppsf(target_price, target_sqft, sold_prices, sqfts)
            
            return {
                "zip_code": zip_code,
                "comps_found": len(sold_prices),
                "comps_used_status": "sold" if params.get('statusCategory') == 'sold' else "active_fallback",
                "analysis": analysis
            }
        else:
            return {"error": f"Failed with status: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import json
    # Testing with '78539' Edinburg
    res = get_recent_comps('78539')
    print(json.dumps(res, indent=4))
