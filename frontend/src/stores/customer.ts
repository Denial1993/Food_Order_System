import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 跨店顧客記憶 — 規格書 3.4。
 * 暱稱存於 LocalStorage,共用主網域時自動帶入,不需後端跨店同步。
 */
const NICK_KEY = 'food.nickname'

export const useCustomerStore = defineStore('customer', () => {
  const nickname = ref<string>(localStorage.getItem(NICK_KEY) ?? '')

  function setNickname(name: string) {
    nickname.value = name.trim()
    if (nickname.value) {
      localStorage.setItem(NICK_KEY, nickname.value)
    } else {
      localStorage.removeItem(NICK_KEY)
    }
  }

  return { nickname, setNickname }
})
