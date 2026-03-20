# VHS tape — run `vhs demo.tape` to generate demo.gif
# Install VHS: https://github.com/charmbracelet/vhs

Output demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 800
Set Height 500
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 40ms

Sleep 500ms

Type "pls 'find all python files bigger than 1MB'"
Sleep 200ms
Enter
Sleep 3s

Sleep 1s
Type "y"
Enter
Sleep 2s

Sleep 1s

Type "pls 'compress all PNGs in this folder' --explain"
Sleep 200ms
Enter
Sleep 3s

Sleep 1s
Type "n"
Enter
Sleep 1s

Sleep 2s
