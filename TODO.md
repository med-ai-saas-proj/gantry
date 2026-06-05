# TODO

## Keycloak

- [x] Refactor keycloak connection config and keycloak service out to a separate module

## router

- [ ] ROUTER

## Admin

- [x] Check admin auth stuffs
- [x] Admin integration
- [x] Think about admin dashboard

## Log

- [ ] Check how the logs work and find a better way to do observability

## Hoang's work

- [x] Restructure folders
- [ ] Check them all
- [ ] Check the RAG
- [ ] Check the file

---

build an api gateway to route requests, checkout @src/gantry/api_gateway/settings.py  @src/gantry/settings/api_gateway.py , @src/gantry/management/api_keys/dependencies.py  

Then it should do the following when a request is hit:
1. Check if route exists
2. Check route rate limit
3. Check if API keys is valid
4. Check api key rate limit
5. Check API key spending limit (I'm not sure if billing is done, should double check, if not done, you should do it)
6. Check API key permissions
7. Hold if auto_hold
8. Forward request
9. Charge if auto_charge

Remember to handle errors.
