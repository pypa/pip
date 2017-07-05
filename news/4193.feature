Add ability to suggest commands and also to autocorrect mistyped commands.

A new "autocorrect" configuration key is now supported. It can be set to a
numerical value. If it is set, pip will wait for the specified seconds and then
autocorrect your command and continue, if a replacement is similar enough.
