// main.go
package main

import "fmt"

func add(x int, y int) int {
    return x + y
}

func main() {
    result := add(5, 6)
    fmt.Println("The sum is", result)
}
