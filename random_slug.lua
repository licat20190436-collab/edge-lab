-- random_slug.lua
-- Use with wrk to randomise the attraction slug on every request,
-- preventing Redis cache warm-up from masking FastAPI memory pressure.
-- Usage: wrk -c 120 -d 30s -t 1 --timeout 20s -s random_slug.lua http://localhost

math.randomseed(os.time())

request = function()
    local slug = "attraction-" .. math.random(0, 499)
    return wrk.format("GET", "/api/attraction/" .. slug)
end
