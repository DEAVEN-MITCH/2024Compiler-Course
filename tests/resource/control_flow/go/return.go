// SimpleReturn 无返回值
func SimpleReturn() {
    fmt.Println("Executing SimpleReturn")
    return
}

// ReturnValue 返回一个整数
func ReturnValue() int {
    return 42
}

// ReturnVariable 返回一个已经声明的变量
func ReturnVariable() string {
    message := "Hello, world!"
    return message
}

// ReturnExpression 返回一个计算表达式的结果
func ReturnExpression(a, b int) int {
    result := a + b
    return result
}

// ReturnMultipleValues 返回多个值
func ReturnMultipleValues() (int, string) {
    return 10, "ten"
}

// ReturnWithError 返回一个错误
func ReturnWithError(value int) (int, error) {
    if value < 0 {
        return 0, errors.New("negative value provided")
    }
    return value, nil
}

// ReturnFromIf 返回从条件语句
func ReturnFromIf(value int) string {
    if value > 0 {
        return "positive"
    } else {
        return "non-positive"
    }
}

// ReturnFromLoop 返回从循环中
func ReturnFromLoop(numbers []int, target int) bool {
    for _, number := range numbers {
        if number == target {
            return true
        }
    }
    return false
}
