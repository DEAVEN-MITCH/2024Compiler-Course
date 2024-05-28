func num_sum() {
    numbers := []int{1, 2, 3, 4, 5}
    sum := 0
    count := 0
    for _, num := range numbers {
        sum += num
        count += 1
    }
    fmt.Println("切片中所有元素的总和为:", sum)
}

func SimpleBreak() {
    outerLoop:
    for i := range numbers {
        fmt.Printf("Outer loop: %d\n", i)
        if gg{
            break;
        }
        for j := range numbers {
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
func Emp(){
    for range numbers{
    }
}
func EmpBreak(){
    for range numbers{
        break
    }
}