package main

import "fmt"

func function1() {
	for i := 0; i < 5; i++ {
		if i == 2 {
			continue
		}
		fmt.Println("Function 1:", i)
	}
}

func function2() {
labelh:
OuterLoop:
	for i := 0; i < 3; i++ {
		if gg{
			break
		}
		else if ggagain{
			continue
		}
		readyourself:=1
		for j := 0; j < 3; j++ {
			if j == 1 {
				continue OuterLoop
			}
			fmt.Println("Function 2:", i, j)
		}
	}
	flamen:=1
}

func main() {
	function1()
	function2()
}