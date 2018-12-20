accept_content = ("json", "pickle")  # celery crashes without a report because of "pickle"
task_serializer = "pickle"
result_serializer = "pickle"

