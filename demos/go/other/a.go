// By: Tom Wambold <tom5760@gmail.com>
package other

import "math"

// A three-value vector (i, j, k)
type Vector3 [3]float

func (a *Vector3) Size() float {
    return float(math.Sqrt(float64(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])));
}
