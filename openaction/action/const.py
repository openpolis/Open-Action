"""
Constants specific to OpenAction application

Action statuses
---------------

* DRAFT: an action has been created but parameters are not all defined.
  Users cannot vote the action
* READY: parameters are all defined, users can vote the action, but the action is
  still not reachable by search engines, nor by site search. Just only with the url

"""

ACTION_STATUS_DRAFT = 'DRAFT'
ACTION_STATUS_READY = 'READY'
ACTION_STATUS_ACTIVE = 'ACTIVE'

# TODO TOCOMPLETE Antonio with documentation

ACTION_STATUS = {
    'draft' : ACTION_STATUS_DRAFT,
    'ready'   : ACTION_STATUS_READY,
    'deleted' : 'CANCELED DRAFT',
    'active' : ACTION_STATUS_ACTIVE,
    'closed' : 'CLOSED',
    'victory' : 'VICTORY',
}
