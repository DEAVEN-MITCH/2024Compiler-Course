func main() {
    fmt.Println("Start")
    goto Skip
    fmt.Println("This will not be printed")
Skip:
    fmt.Println("Skipped to here")

    for i := 0; i < 5; i++ {
        if i == 2 {
            goto Found
        }
    }
    fmt.Println("Not found")
Found:
    fmt.Println("Found at 2")

    if true {
        goto InsideIf
    } else {
        fmt.Println("In the else block")
    }
InsideIf:
    fmt.Println("Inside if block")

    // Example of undefined label (will not compile but good for testing parser logic)
    // goto UndefinedLabel
}
