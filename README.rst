.. image:: https://travis-ci.org/ProzorroUKR/prozorro_tasks.svg?branch=master
    :target: https://travis-ci.org/ProzorroUKR/prozorro_tasks

.. image:: https://coveralls.io/repos/github/ProzorroUKR/prozorro_tasks/badge.svg?branch=master
    :target: https://coveralls.io/github/ProzorroUKR/prozorro_tasks?branch=master



Distributed task manager
========================

*One Ring to rule them all*


Feed process start
------------------

kubectl exec -it <pod-name>  -- /bin/bash

# python
>>> from crawler.tasks import process_feed
>>> process_feed.delay(mode="_all_")

