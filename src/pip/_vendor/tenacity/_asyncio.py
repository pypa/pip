# -*- coding: utf-8 -*-
# Copyright 2016 Étienne Bersac
# Copyright 2016 Julien Danjou
# Copyright 2016 Joshua Harlow
# Copyright 2013-2014 Ray Holder
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import asyncio
except ImportError:
    asyncio = None

import sys

from tenacity import BaseRetrying
from tenacity import DoAttempt
from tenacity import DoSleep
from tenacity import RetryCallState


if asyncio:
    class AsyncRetrying(BaseRetrying):

        def __init__(self,
                     sleep=asyncio.sleep,
                     **kwargs):
            super(AsyncRetrying, self).__init__(**kwargs)
            self.sleep = sleep

        def wraps(self, fn):
            fn = super().wraps(fn)
            # Ensure wrapper is recognized as a coroutine function.
            fn._is_coroutine = asyncio.coroutines._is_coroutine
            return fn

        @asyncio.coroutine
        def call(self, fn, *args, **kwargs):
            self.begin(fn)

            retry_state = RetryCallState(
                retry_object=self, fn=fn, args=args, kwargs=kwargs)
            while True:
                do = self.iter(retry_state=retry_state)
                if isinstance(do, DoAttempt):
                    try:
                        result = yield from fn(*args, **kwargs)
                    except BaseException:
                        retry_state.set_exception(sys.exc_info())
                    else:
                        retry_state.set_result(result)
                elif isinstance(do, DoSleep):
                    retry_state.prepare_for_next_attempt()
                    yield from self.sleep(do)
                else:
                    return do
