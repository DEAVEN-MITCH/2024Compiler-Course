type Calculator struct{}

func (c Calculator) Clear() {
    fmt.Println("Calculator cleared")
}

type Rectangle struct {
    width, height float64
}

func (r Rectangle) Area() float64 {
    return r.width * r.height
}
