To start the bot, run main.py


IMPORTANT NOTES:
----------------
- When you create a delayed job you should use methods utils.add_job_by_delay and utils.add_job_by_date.
That way it is logged, and it gets a specific job id, containing user id. (Which is used in user`s tasks removing mechanism)
- To remove the task, use the utils.remove_job
- To remove all tasks of a specific user, use utils.remove_all_user_jobs
- To turn on the test mode, add a function timings.test_mode() in main. That will turn  
the flag  TEST_MODE in main.py to true and turn all the timings to test times (several seconds)
- 

TELEGRAM API NOTES
-------------
- Bot can not send more than 30 messages per second, so ths should be avoided in massive 
messages mailing through distributing all the messages in an interval of time, using
utils.generate_random_number_for_n_users and daily_message_sending_shift 
to get random time shifts for all tasks in the same time at the end of the day  
(this only works if you know, how many users will be receiving the message)  
In case of a Flood (more than 30 messages per second, 429 response will be raised by telegram)

NOT IMPLEMENTED YET
------------

[//]: # (- Support of 21 000 messages sent at once is not supported yet &#40;since it will take up to an hour to send all the messages&#41;)

[//]: # (File start_parameters.txt in root must contain one of 2 words: "test" or "prod")

[//]: # (If "test" is in the file, program runs in test mode: all the timings are shorter &#40;seconds instead of miuntes &#40;all divided by 60 as for 09.09.2025 version&#41;&#41;)

[//]: # ()
[//]: # (If "prod" is in file, everything runs as it should in prod version)

TODO: write everything else
-------------
