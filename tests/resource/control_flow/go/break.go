package main

import "fmt"

func main() {
    outerLoop:
    for i := 0; i < 3; i++ {
        fmt.Printf("Outer loop: %d\n", i)
        if gg{
            break;
        }
        for j := 0; j < 3; j++ {
            fmt.Printf("Inner loop: %d\n", j)
            if j == 1 {
                break outerLoop
            }
            if j>6{
                break;
                continue
            }
        }
    }
    eex+1
}
func a(){
    for ; ;{

    }
    for ;b ;{

    }
    end();
}