const express = require("express");
// const mongoose = require('mongoose');

const cors = require("cors");
const app = express();
const User = require("./db/User");
const Product = require("./db/Product");
require("./db/config");


const Jwt = require("jsonwebtoken");
const JwtKey = "e-comm";

app.use(express.json());
app.use(cors());
// app.get("/",(req,resp)=>{
// resp.send("app is working.....")
// });

// const connectDB = async () => {
//     await mongoose.connect('mongodb://localhost:27017/e-comm');
//     const productSchema = new mongoose.Schema({});
//     const product = mongoose.model('product', productSchema);
//     const data = await product.find();
//     console.warn(data);
// }
// connectDB();

app.post("/register", async (req, resp) => {
    // resp.send("api is working")
    let user = new User(req.body);
    let result = await user.save();
    result = result.toObject();
    delete result.password;

    Jwt.sign({ result }, JwtKey, { expiresIn: "15m" }, (err, token) => {
        resp.send({ result, auth: token });
    })

})


app.post("/login", async (req, resp) => {
    console.log(req.body);
    if (req.body.password && req.body.email) {
        let user = await User.findOne(req.body).select("-password");
        if (user) {
            Jwt.sign({ user }, JwtKey, { expiresIn: "15m" }, (err, token) => {
                resp.send({ user, auth: token });
            })

        }
        else {
            resp.send({ result: "No user found" })
        }
    }
    else {
        resp.send({ result: "Please enter email and password" })
    }


})

app.post("/add-product", verifyToken, async (req, resp) => {
    let product = new Product(req.body);
    let result = await product.save();
    resp.send(result);
})

app.get("/products", verifyToken, async (req, resp) => {
    let products = await Product.find();
    if (products.length > 0) {
        resp.send(products);
    }
    else {
        resp.send({ result: "No products found" })
    }
})


app.delete("/product/:id", async (req, resp) => {
    const result = await Product.deleteOne({ _id: req.params.id })
    if (result) {
        resp.send(result);
    }
    else {
        resp.send({ result: "No product found" })
    }
});

app.get("/product/:id", async (req, resp) => {
    let result = await Product.findOne({ _id: req.params.id })
    if (result) {
        resp.send(result)
    } else {
        resp.send({ result: "No record found" })
    }
})

app.put("/product/:id", async (req, resp) => {
    let result = await Product.updateOne(
        { _id: req.params.id },
        {
            $set: req.body
        }
    )
    resp.send(result)
});

app.get("/search/:key", async (req, resp) => {
    let result = await Product.find({
        "$or": [
            { name: { $regex: req.params.key } },
            { company: { $regex: req.params.key } },
            { category: { $regex: req.params.key } }
        ]
    });
    resp.send(result)
})


function verifyToken(req, resp, next) {
    let token = req.headers['authorization'];
    if (token) {
        token = token.split(" ")[1];
        Jwt.verify(token, JwtKey, (err, valid) => {
            if (valid) {
                next();
            }
            else {
                resp.send({ result: "Please provide valid token" })
            }
        })
    }
    else {
        resp.send({ result: "Please provide token" })
    }
}

app.listen(5000, () => {
    console.warn("Server is running on port 5000");
});